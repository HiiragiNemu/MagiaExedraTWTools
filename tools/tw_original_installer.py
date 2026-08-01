#!/usr/bin/env python3
"""Validate, download, install, update, verify, and roll back the original TW XAPK.

The implementation uses only the Python standard library. It never modifies an
APK and never reads game-account data. Device installation always goes through
``adb install-multiple -r -i com.android.vending`` while adbd is temporarily in
shell mode when necessary.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterable
from xml.etree import ElementTree


PACKAGE_NAME = "tw.sonet.magiaexedra"
INSTALLER_PACKAGE = "com.android.vending"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_MANIFEST = REPOSITORY_ROOT / "manifests" / "known-releases.json"
ROLE_FILENAMES = {
    "": "base.apk",
    "base_assets": "split_base_assets.apk",
    "config.arm64_v8a": "split_config.arm64_v8a.apk",
}
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_XAPK_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_APK_ENTRIES = 16
MAX_TOTAL_APK_BYTES = 4 * 1024 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024 * 1024
DOWNLOAD_CHUNK = 1024 * 1024
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ToolError(RuntimeError):
    """Expected, user-actionable installer error."""


@dataclasses.dataclass(frozen=True)
class ApkIdentity:
    role: str
    path: str
    package: str
    split: str
    version_name: str | None
    version_code: str | None
    length: int
    sha256: str


@dataclasses.dataclass(frozen=True)
class XapkIdentity:
    path: str
    length: int
    sha256: str
    version_name: str | None
    version_code: str | None
    apks: tuple[ApkIdentity, ...]


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    path: str
    length: int
    sha256: str
    resumed_from: int
    response_status: int
    reused_not_modified: bool


@dataclasses.dataclass(frozen=True)
class ArtifactPin:
    length: int
    sha256: str


@dataclasses.dataclass(frozen=True)
class ReleasePin:
    version_name: str
    version_code: str
    xapk: ArtifactPin
    splits: dict[str, ArtifactPin]


@dataclasses.dataclass(frozen=True)
class ReleaseManifest:
    path: str
    latest_version: str
    latest_endpoint: str
    releases: dict[str, ReleasePin]

    @property
    def latest(self) -> ReleasePin:
        return self.releases[self.latest_version]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(DOWNLOAD_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def normalize_sha256(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if not SHA256_PATTERN.fullmatch(normalized):
        raise ToolError(f"{label} must be exactly 64 hexadecimal SHA-256 characters")
    return normalized


def _positive_bounded_length(value: Any, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ToolError(f"{label} must be a positive integer")
    if value > maximum:
        raise ToolError(f"{label} exceeds the {maximum}-byte safety limit")
    return value


def load_release_manifest(path: Path = DEFAULT_RELEASE_MANIFEST) -> ReleaseManifest:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as error:
        raise ToolError(f"Release manifest not found: {path}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ToolError(f"Release manifest is unreadable: {error}") from error
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise ToolError("Release manifest schemaVersion must be 1")
    if data.get("packageName") != PACKAGE_NAME:
        raise ToolError(f"Release manifest packageName must be {PACKAGE_NAME}")
    latest_version = data.get("latestVersion")
    latest_endpoint = data.get("latestEndpoint")
    if not isinstance(latest_version, str) or not latest_version.strip():
        raise ToolError("Release manifest latestVersion is required")
    if not isinstance(latest_endpoint, str):
        raise ToolError("Release manifest latestEndpoint is required")
    endpoint = urllib.parse.urlsplit(latest_endpoint)
    if endpoint.scheme != "https" or not endpoint.hostname or endpoint.username or endpoint.password:
        raise ToolError("Release manifest latestEndpoint must be a credential-free HTTPS URL")
    raw_releases = data.get("releases")
    if not isinstance(raw_releases, list) or not raw_releases:
        raise ToolError("Release manifest releases must be a non-empty array")
    releases: dict[str, ReleasePin] = {}
    expected_split_keys = {"base", "base_assets", "config.arm64_v8a"}
    seen_version_codes: set[str] = set()
    for index, raw in enumerate(raw_releases):
        label = f"releases[{index}]"
        if not isinstance(raw, dict):
            raise ToolError(f"{label} must be an object")
        version_name = raw.get("versionName")
        version_code_raw = raw.get("versionCode")
        if not isinstance(version_name, str) or not version_name.strip():
            raise ToolError(f"{label}.versionName is required")
        if isinstance(version_code_raw, bool) or not isinstance(version_code_raw, int) or version_code_raw <= 0:
            raise ToolError(f"{label}.versionCode must be a positive integer")
        version_code = str(version_code_raw)
        if version_name in releases or version_code in seen_version_codes:
            raise ToolError("Release manifest versions and versionCodes must be unique")
        seen_version_codes.add(version_code)
        xapk_pin = ArtifactPin(
            length=_positive_bounded_length(raw.get("length"), f"{label}.length", MAX_DOWNLOAD_BYTES),
            sha256=normalize_sha256(str(raw.get("sha256", "")), f"{label}.sha256"),
        )
        raw_splits = raw.get("splits")
        if not isinstance(raw_splits, dict) or set(raw_splits) != expected_split_keys:
            raise ToolError(f"{label}.splits must contain exactly {sorted(expected_split_keys)}")
        splits: dict[str, ArtifactPin] = {}
        for split_name in sorted(expected_split_keys):
            raw_pin = raw_splits[split_name]
            if not isinstance(raw_pin, dict):
                raise ToolError(f"{label}.splits.{split_name} must be an object")
            splits[split_name] = ArtifactPin(
                length=_positive_bounded_length(
                    raw_pin.get("length"), f"{label}.splits.{split_name}.length", MAX_TOTAL_APK_BYTES
                ),
                sha256=normalize_sha256(
                    str(raw_pin.get("sha256", "")), f"{label}.splits.{split_name}.sha256"
                ),
            )
        releases[version_name] = ReleasePin(version_name, version_code, xapk_pin, splits)
    if latest_version not in releases:
        raise ToolError("Release manifest latestVersion does not identify a listed release")
    return ReleaseManifest(str(path.resolve()), latest_version, latest_endpoint, releases)


def enforce_xapk_trust(
    identity: XapkIdentity,
    manifest: ReleaseManifest,
    supplied_sha256: str | None,
    *,
    require_latest: bool = False,
) -> ReleasePin | None:
    release = manifest.releases.get(identity.version_name or "")
    if require_latest and (release is None or release.version_name != manifest.latest_version):
        raise ToolError(
            f"Downloaded XAPK version {identity.version_name!r} is not manifest latestVersion {manifest.latest_version!r}"
        )
    if release is None:
        if supplied_sha256 is None:
            raise ToolError(
                f"Unknown XAPK version {identity.version_name!r}; provide a separately trusted --expected-xapk-sha256"
            )
        trusted = normalize_sha256(supplied_sha256, "--expected-xapk-sha256")
        if identity.sha256 != trusted:
            raise ToolError(f"Unknown-version XAPK SHA-256 mismatch: {identity.sha256}")
        return None
    if supplied_sha256 is not None:
        supplied = normalize_sha256(supplied_sha256, "--expected-xapk-sha256")
        if supplied != release.xapk.sha256:
            raise ToolError("A known release cannot override the repository release-manifest SHA-256")
    if identity.version_code != release.version_code:
        raise ToolError(
            f"Known release versionCode mismatch: {identity.version_code!r} expected {release.version_code!r}"
        )
    if identity.length != release.xapk.length or identity.sha256 != release.xapk.sha256:
        raise ToolError(
            f"Known release XAPK length/SHA-256 mismatch: bytes={identity.length} sha256={identity.sha256}"
        )
    actual_splits = {apk.split or "base": apk for apk in identity.apks}
    for split_name, pin in release.splits.items():
        apk = actual_splits[split_name]
        if apk.length != pin.length or apk.sha256 != pin.sha256:
            raise ToolError(
                f"Known release split {split_name} length/SHA-256 mismatch: bytes={apk.length} sha256={apk.sha256}"
            )
    return release


def sanitized_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    hostname = parsed.hostname or ""
    if parsed.port:
        hostname += f":{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, hostname, parsed.path, "", ""))


def _read_length8(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise ToolError("Truncated UTF-8 string length in AndroidManifest.xml")
    first = data[offset]
    offset += 1
    if first & 0x80:
        if offset >= len(data):
            raise ToolError("Truncated UTF-8 string length in AndroidManifest.xml")
        return ((first & 0x7F) << 8) | data[offset], offset + 1
    return first, offset


def _read_length16(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ToolError("Truncated UTF-16 string length in AndroidManifest.xml")
    first = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    if first & 0x8000:
        if offset + 2 > len(data):
            raise ToolError("Truncated UTF-16 string length in AndroidManifest.xml")
        second = struct.unpack_from("<H", data, offset)[0]
        return ((first & 0x7FFF) << 16) | second, offset + 2
    return first, offset


def _parse_string_pool(data: bytes, chunk_offset: int) -> list[str]:
    if chunk_offset + 28 > len(data):
        raise ToolError("Truncated Android binary XML string pool")
    _, header_size, chunk_size, string_count, _, flags, strings_start, _ = struct.unpack_from(
        "<HHIIIIII", data, chunk_offset
    )
    if header_size < 28 or chunk_size < header_size or chunk_offset + chunk_size > len(data):
        raise ToolError("Invalid Android binary XML string pool")
    if string_count > 1_000_000:
        raise ToolError("Unreasonable Android binary XML string count")
    offsets_end = chunk_offset + header_size + (string_count * 4)
    if offsets_end > chunk_offset + chunk_size:
        raise ToolError("Truncated Android binary XML string offsets")
    is_utf8 = bool(flags & 0x100)
    values: list[str] = []
    for index in range(string_count):
        relative = struct.unpack_from("<I", data, chunk_offset + header_size + index * 4)[0]
        position = chunk_offset + strings_start + relative
        if not chunk_offset <= position < chunk_offset + chunk_size:
            raise ToolError("Invalid Android binary XML string offset")
        if is_utf8:
            _, position = _read_length8(data, position)
            byte_length, position = _read_length8(data, position)
            end = position + byte_length
            if end > len(data):
                raise ToolError("Truncated UTF-8 Android binary XML string")
            values.append(data[position:end].decode("utf-8", errors="strict"))
        else:
            char_length, position = _read_length16(data, position)
            end = position + char_length * 2
            if end > len(data):
                raise ToolError("Truncated UTF-16 Android binary XML string")
            values.append(data[position:end].decode("utf-16le", errors="strict"))
    return values


def _typed_value(data_type: int, data_value: int, strings: list[str]) -> str | None:
    if data_type == 0x03 and data_value < len(strings):
        return strings[data_value]
    if data_type in {0x10, 0x11, 0x12}:
        return str(data_value)
    return None


def parse_android_manifest(data: bytes) -> dict[str, str]:
    if len(data) > MAX_MANIFEST_BYTES:
        raise ToolError("AndroidManifest.xml exceeds the safety limit")
    stripped = data.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped.startswith(b"<"):
        try:
            root = ElementTree.fromstring(stripped)
        except ElementTree.ParseError as error:
            raise ToolError(f"Invalid text AndroidManifest.xml: {error}") from error
        if root.tag.rsplit("}", 1)[-1] != "manifest":
            raise ToolError("AndroidManifest.xml has no manifest root")
        return {key.rsplit("}", 1)[-1]: value for key, value in root.attrib.items()}

    if len(data) < 8 or struct.unpack_from("<H", data, 0)[0] != 0x0003:
        raise ToolError("Unsupported AndroidManifest.xml encoding")
    offset = struct.unpack_from("<H", data, 2)[0]
    strings: list[str] | None = None
    while offset + 8 <= len(data):
        chunk_type, _, chunk_size = struct.unpack_from("<HHI", data, offset)
        if chunk_size < 8 or offset + chunk_size > len(data):
            raise ToolError(f"Invalid Android binary XML chunk at offset {offset}")
        if chunk_type == 0x0001:
            strings = _parse_string_pool(data, offset)
        elif chunk_type == 0x0102:
            if strings is None:
                raise ToolError("Android XML element precedes its string pool")
            if offset + 36 > len(data):
                raise ToolError("Truncated Android XML start element")
            name_index = struct.unpack_from("<I", data, offset + 20)[0]
            if name_index >= len(strings):
                raise ToolError("Invalid Android XML element name")
            if strings[name_index] == "manifest":
                attribute_start, attribute_size, attribute_count = struct.unpack_from(
                    "<HHH", data, offset + 24
                )
                if attribute_size < 20 or attribute_count > 4096:
                    raise ToolError("Invalid Android manifest attributes")
                first_attribute = offset + 16 + attribute_start
                values: dict[str, str] = {}
                for index in range(attribute_count):
                    current = first_attribute + index * attribute_size
                    if current + 20 > offset + chunk_size:
                        raise ToolError("Truncated Android manifest attribute")
                    name, raw_value = struct.unpack_from("<II", data, current + 4)
                    data_type = data[current + 15]
                    data_value = struct.unpack_from("<I", data, current + 16)[0]
                    if name >= len(strings):
                        continue
                    value: str | None = None
                    if raw_value != 0xFFFFFFFF and raw_value < len(strings):
                        value = strings[raw_value]
                    else:
                        value = _typed_value(data_type, data_value, strings)
                    if value is not None:
                        values[strings[name]] = value
                return values
        offset += chunk_size
    raise ToolError("AndroidManifest.xml manifest element was not found")


def inspect_apk(path: Path, role: str) -> ApkIdentity:
    try:
        with zipfile.ZipFile(path) as archive:
            try:
                info = archive.getinfo("AndroidManifest.xml")
            except KeyError as error:
                raise ToolError(f"APK has no AndroidManifest.xml: {path.name}") from error
            if info.file_size > MAX_MANIFEST_BYTES:
                raise ToolError(f"APK manifest exceeds the safety limit: {path.name}")
            manifest = parse_android_manifest(archive.read(info))
    except zipfile.BadZipFile as error:
        raise ToolError(f"Invalid APK ZIP: {path.name}") from error
    package = manifest.get("package", "")
    split = manifest.get("split", "")
    if package != PACKAGE_NAME:
        raise ToolError(f"APK package {package!r} is not {PACKAGE_NAME!r}: {path.name}")
    if split not in ROLE_FILENAMES:
        raise ToolError(f"Unexpected APK split {split!r}: {path.name}")
    return ApkIdentity(
        role=role,
        path=str(path.resolve()),
        package=package,
        split=split,
        version_name=manifest.get("versionName"),
        version_code=manifest.get("versionCode"),
        length=path.stat().st_size,
        sha256=sha256_file(path),
    )


def _stream_zip_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    with archive.open(info) as source, temporary.open("wb") as target:
        shutil.copyfileobj(source, target, DOWNLOAD_CHUNK)
        target.flush()
        os.fsync(target.fileno())
    if temporary.stat().st_size != info.file_size:
        raise ToolError(f"XAPK member length mismatch: {info.filename}")
    os.replace(temporary, destination)


def extract_and_validate_xapk(xapk_path: Path, destination: Path) -> XapkIdentity:
    if not xapk_path.is_file():
        raise ToolError(f"XAPK not found: {xapk_path}")
    destination.mkdir(parents=True, exist_ok=True)
    xapk_hash = sha256_file(xapk_path)
    xapk_length = xapk_path.stat().st_size
    try:
        with zipfile.ZipFile(xapk_path) as archive:
            apk_entries = [info for info in archive.infolist() if info.filename.lower().endswith(".apk")]
            if len(apk_entries) != 3:
                raise ToolError(f"XAPK must contain exactly three APK entries; found {len(apk_entries)}")
            if len(apk_entries) > MAX_APK_ENTRIES:
                raise ToolError("XAPK contains too many APK entries")
            total_size = sum(info.file_size for info in apk_entries)
            if total_size <= 0 or total_size > MAX_TOTAL_APK_BYTES:
                raise ToolError("XAPK APK payload size is outside the safety limit")
            for info in apk_entries:
                if info.flag_bits & 0x1:
                    raise ToolError(f"Encrypted XAPK APK member is not accepted: {info.filename}")
                if info.compress_size <= 0 or info.file_size / info.compress_size > 200:
                    raise ToolError(f"Suspicious XAPK compression ratio: {info.filename}")

            xapk_manifest: dict[str, Any] = {}
            with contextlib.suppress(KeyError):
                manifest_info = archive.getinfo("manifest.json")
                if manifest_info.file_size > MAX_XAPK_MANIFEST_BYTES:
                    raise ToolError("XAPK manifest.json exceeds the safety limit")
                try:
                    xapk_manifest = json.loads(archive.read(manifest_info).decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ToolError(f"Invalid XAPK manifest.json: {error}") from error
                declared_package = xapk_manifest.get("package_name") or xapk_manifest.get("packageName")
                if declared_package and declared_package != PACKAGE_NAME:
                    raise ToolError(f"XAPK declares unexpected package {declared_package!r}")

            staged: list[Path] = []
            for index, info in enumerate(apk_entries):
                if info.is_dir() or info.file_size <= 0:
                    raise ToolError(f"Invalid XAPK APK member: {info.filename}")
                path = destination / f"candidate-{index}.apk"
                _stream_zip_entry(archive, info, path)
                staged.append(path)
    except zipfile.BadZipFile as error:
        raise ToolError(f"Invalid XAPK ZIP: {xapk_path}") from error

    identities: dict[str, ApkIdentity] = {}
    for path in staged:
        preliminary = inspect_apk(path, "candidate")
        if preliminary.split in identities:
            raise ToolError(f"XAPK contains duplicate split {preliminary.split!r}")
        final_path = destination / ROLE_FILENAMES[preliminary.split]
        os.replace(path, final_path)
        identities[preliminary.split] = inspect_apk(final_path, ROLE_FILENAMES[preliminary.split])
    missing = [split or "<base>" for split in ROLE_FILENAMES if split not in identities]
    if missing:
        raise ToolError("XAPK is missing required splits: " + ", ".join(missing))

    version_names = {identity.version_name for identity in identities.values() if identity.version_name}
    version_codes = {identity.version_code for identity in identities.values() if identity.version_code}
    if len(version_names) > 1 or len(version_codes) > 1:
        raise ToolError("XAPK APK splits do not declare one consistent version")

    base = identities[""]
    version_name = str(xapk_manifest.get("version_name") or xapk_manifest.get("versionName") or base.version_name or "") or None
    raw_version_code = xapk_manifest.get("version_code") or xapk_manifest.get("versionCode") or base.version_code
    version_code = str(raw_version_code) if raw_version_code not in (None, "") else None
    if base.version_name and version_name and base.version_name != version_name:
        raise ToolError("XAPK/base versionName mismatch")
    if base.version_code and version_code and base.version_code != version_code:
        raise ToolError("XAPK/base versionCode mismatch")
    ordered = tuple(identities[split] for split in ROLE_FILENAMES)
    return XapkIdentity(
        path=str(xapk_path.resolve()),
        length=xapk_length,
        sha256=xapk_hash,
        version_name=version_name,
        version_code=version_code,
        apks=ordered,
    )


def _build_opener(proxy: str | None) -> urllib.request.OpenerDirector:
    handlers: list[Any] = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def _usable_if_range(metadata: dict[str, Any]) -> str | None:
    etag = str(metadata.get("etag") or "").strip()
    if etag and not etag.lower().startswith("w/"):
        return etag
    last_modified = str(metadata.get("lastModified") or "").strip()
    return last_modified or None


def _parse_content_range(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    match = re.fullmatch(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", value.strip(), re.IGNORECASE)
    if not match or match.group(3) == "*":
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def download_file(
    url: str,
    destination: Path,
    *,
    proxy: str | None = None,
    expected_sha256: str | None = None,
    expected_size: int | None = None,
) -> DownloadResult:
    if expected_sha256 is not None:
        expected_sha256 = normalize_sha256(expected_sha256, "expected download SHA-256")
    if expected_size is not None:
        _positive_bounded_length(expected_size, "expected download size", MAX_DOWNLOAD_BYTES)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    partial_meta_path = destination.with_name(destination.name + ".part.json")
    final_meta_path = destination.with_name(destination.name + ".download.json")
    partial_meta = read_json(partial_meta_path, {}) or {}
    final_meta = read_json(final_meta_path, {}) or {}
    request_headers = {
        "User-Agent": "MagiaExedraTWTools/1.0",
        "Accept-Encoding": "identity",
    }

    existing = partial.stat().st_size if partial.is_file() else 0
    stream_limit = min(MAX_DOWNLOAD_BYTES, expected_size) if expected_size is not None else MAX_DOWNLOAD_BYTES
    if existing > stream_limit:
        raise ToolError(f"Partial download already exceeds the {stream_limit}-byte trusted limit")
    if_range = _usable_if_range(partial_meta)
    resume_allowed = existing > 0 and partial_meta.get("url") == sanitized_url(url) and bool(if_range)
    if resume_allowed:
        request_headers["Range"] = f"bytes={existing}-"
        request_headers["If-Range"] = str(if_range)
    elif destination.is_file() and final_meta.get("url") == sanitized_url(url):
        if final_meta.get("etag"):
            request_headers["If-None-Match"] = str(final_meta["etag"])
        elif final_meta.get("lastModified"):
            request_headers["If-Modified-Since"] = str(final_meta["lastModified"])

    request = urllib.request.Request(url, headers=request_headers, method="GET")
    opener = _build_opener(proxy)
    try:
        response = opener.open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code == 304 and destination.is_file():
            digest = sha256_file(destination)
            length = destination.stat().st_size
            if length > MAX_DOWNLOAD_BYTES:
                raise ToolError("Cached XAPK exceeds the download safety limit") from error
            if expected_sha256 and digest != expected_sha256.lower():
                raise ToolError(f"Cached XAPK SHA-256 mismatch: {digest}") from error
            if expected_size is not None and length != expected_size:
                raise ToolError(f"Cached XAPK length mismatch: {length}") from error
            return DownloadResult(str(destination.resolve()), length, digest, 0, 304, True)
        if error.code == 416 and resume_allowed:
            content_range = error.headers.get("Content-Range", "")
            match = re.fullmatch(r"bytes\s+\*/(\d+)", content_range.strip(), re.IGNORECASE)
            if match and int(match.group(1)) == existing:
                if existing > MAX_DOWNLOAD_BYTES:
                    raise ToolError("Completed partial XAPK exceeds the download safety limit") from error
                digest = sha256_file(partial)
                if expected_sha256 and digest != expected_sha256.lower():
                    raise ToolError(f"Completed partial XAPK SHA-256 mismatch: {digest}") from error
                if expected_size is not None and existing != expected_size:
                    raise ToolError(f"Completed partial XAPK length mismatch: {existing}") from error
                os.replace(partial, destination)
                metadata = {
                    "url": sanitized_url(url),
                    "length": existing,
                    "sha256": digest,
                    "completedAt": utc_now(),
                    "etag": partial_meta.get("etag"),
                    "lastModified": partial_meta.get("lastModified"),
                }
                atomic_write_json(final_meta_path, metadata)
                partial_meta_path.unlink(missing_ok=True)
                return DownloadResult(str(destination.resolve()), existing, digest, existing, 416, False)
        raise ToolError(f"Download failed with HTTP {error.code}: {error.reason}") from error
    except OSError as error:
        raise ToolError(f"Download failed: {error}") from error

    with response:
        status = int(response.getcode() or 200)
        if response.headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
            raise ToolError("Download server returned encoded content; byte-range safety cannot be verified")
        content_range = _parse_content_range(response.headers.get("Content-Range"))
        if status == 206:
            if not resume_allowed or content_range is None or content_range[0] != existing:
                raise ToolError("Download server returned an invalid Content-Range")
            content_length = response.headers.get("Content-Length")
            range_length = content_range[1] - content_range[0] + 1
            if content_range[1] < content_range[0] or content_range[1] >= content_range[2] or (
                content_length and content_length.isdigit() and int(content_length) != range_length
            ):
                raise ToolError("Download Content-Length does not match Content-Range")
            mode = "ab"
            resumed_from = existing
            expected_total = content_range[2]
        elif status == 200:
            mode = "wb"
            resumed_from = 0
            content_length = response.headers.get("Content-Length")
            expected_total = int(content_length) if content_length and content_length.isdigit() else None
        else:
            raise ToolError(f"Unexpected download HTTP status: {status}")
        if expected_total is not None and expected_total > MAX_DOWNLOAD_BYTES:
            raise ToolError("Download exceeds the configured safety limit")
        if expected_total is not None and expected_size is not None and expected_total != expected_size:
            raise ToolError(
                f"Download response length {expected_total} does not match trusted expected size {expected_size}"
            )
        current_meta = {
            "url": sanitized_url(url),
            "etag": response.headers.get("ETag"),
            "lastModified": response.headers.get("Last-Modified"),
            "startedAt": utc_now(),
        }
        atomic_write_json(partial_meta_path, current_meta)
        with partial.open(mode) as target:
            written = resumed_from
            while True:
                block = response.read(DOWNLOAD_CHUNK)
                if not block:
                    break
                if written + len(block) > stream_limit:
                    raise ToolError(f"Download stream exceeds the {stream_limit}-byte trusted limit")
                target.write(block)
                written += len(block)
            target.flush()
            os.fsync(target.fileno())

    length = partial.stat().st_size
    if expected_total is not None and length != expected_total:
        raise ToolError(f"Incomplete download: {length} of {expected_total} bytes")
    if expected_size is not None and length != expected_size:
        raise ToolError(f"Downloaded XAPK length mismatch: {length} (expected {expected_size})")
    digest = sha256_file(partial)
    if expected_sha256 and digest != expected_sha256.lower():
        raise ToolError(f"Downloaded XAPK SHA-256 mismatch: {digest}")
    os.replace(partial, destination)
    metadata = {
        "url": sanitized_url(url),
        "length": length,
        "sha256": digest,
        "completedAt": utc_now(),
        "etag": current_meta.get("etag"),
        "lastModified": current_meta.get("lastModified"),
    }
    atomic_write_json(final_meta_path, metadata)
    partial_meta_path.unlink(missing_ok=True)
    return DownloadResult(str(destination.resolve()), length, digest, resumed_from, status, False)


class AdbRunner:
    def __init__(self, executable: str, serial: str, log_path: Path):
        resolved = shutil.which(executable)
        if resolved is None and Path(executable).is_file():
            resolved = str(Path(executable).resolve())
        if resolved is None:
            raise ToolError(f"adb executable not found: {executable}")
        self.executable = resolved
        self.serial = serial
        self.log_path = log_path

    def run(self, arguments: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        command_arguments = [str(value) for value in arguments]
        try:
            result = subprocess.run(
                [self.executable, "-s", self.serial, *command_arguments],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                shell=False,
            )
        except OSError as error:
            raise ToolError(f"adb could not start: {error}") from error
        record = {
            "at": utc_now(),
            "arguments": command_arguments,
            "exitCode": result.returncode,
            "stdout": result.stdout.strip()[:4000],
            "stderr": result.stderr.strip()[:4000],
        }
        with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        if check and result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise ToolError(f"adb command failed ({result.returncode}): {message}")
        return result


def parse_installer(source: str, dump: str) -> str | None:
    for value in (source, dump):
        match = re.search(
            r"(?:installerPackageName|Installer package name)\s*[=:]\s*([^\s]+)",
            value,
            re.IGNORECASE,
        )
        if match:
            return None if match.group(1) == "null" else match.group(1)
    return None


def package_snapshot(adb: AdbRunner) -> dict[str, Any]:
    paths_result = adb.run(["shell", "pm", "path", PACKAGE_NAME], check=False)
    paths = [line.removeprefix("package:").strip() for line in paths_result.stdout.splitlines() if line.startswith("package:")]
    installed = bool(paths)
    dump = ""
    source = ""
    if installed:
        dump = adb.run(["shell", "dumpsys", "package", PACKAGE_NAME]).stdout
        source = adb.run(["shell", "cmd", "package", "get-install-source", PACKAGE_NAME], check=False).stdout
    version_name_match = re.search(r"^\s*versionName=([^\s]+)", dump, re.MULTILINE)
    version_code_match = re.search(r"^\s*versionCode=(\d+)", dump, re.MULTILINE)
    return {
        "packageName": PACKAGE_NAME,
        "installed": installed,
        "versionName": version_name_match.group(1) if version_name_match else None,
        "versionCode": version_code_match.group(1) if version_code_match else None,
        "installerPackageName": parse_installer(source, dump),
        "apkPaths": paths,
    }


def _safe_leaf(remote_path: str) -> str:
    leaf = remote_path.rsplit("/", 1)[-1]
    if leaf not in set(ROLE_FILENAMES.values()):
        raise ToolError(f"Unexpected installed APK path: {remote_path}")
    return leaf


def backup_current_apks(adb: AdbRunner, before: dict[str, Any], directory: Path) -> list[dict[str, Any]]:
    if not before["installed"]:
        return []
    directory.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for remote in before["apkPaths"]:
        leaf = _safe_leaf(remote)
        destination = directory / leaf
        adb.run(["pull", remote, str(destination)])
        if not destination.is_file() or destination.stat().st_size <= 0:
            raise ToolError(f"ADB did not produce the backup APK: {leaf}")
        expected_split = next(split for split, file_name in ROLE_FILENAMES.items() if file_name == leaf)
        identity = inspect_apk(destination, f"previous-{leaf}")
        if identity.split != expected_split:
            raise ToolError(f"Previous APK backup has the wrong split identity: {leaf}")
        if before.get("versionName") and identity.version_name and identity.version_name != before["versionName"]:
            raise ToolError(f"Previous APK backup versionName mismatch: {leaf}")
        if before.get("versionCode") and identity.version_code and identity.version_code != before["versionCode"]:
            raise ToolError(f"Previous APK backup versionCode mismatch: {leaf}")
        records.append(
            {
                "remotePath": remote,
                "fileName": leaf,
                "length": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "manifest": dataclasses.asdict(identity),
            }
        )
    expected = {_safe_leaf(path) for path in before["apkPaths"]}
    if {record["fileName"] for record in records} != expected:
        raise ToolError("Previous APK backup is incomplete")
    return records


ROLLBACK_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, shutil, subprocess, sys

PACKAGE = "tw.sonet.magiaexedra"
root = pathlib.Path(__file__).resolve().parent
before = json.loads((root / "before.json").read_text(encoding="utf-8-sig"))
parser = argparse.ArgumentParser(description="Restore the package state captured before TW installation")
parser.add_argument("--serial", default=before["serial"])
parser.add_argument("--adb", default="adb")
args = parser.parse_args()
adb = shutil.which(args.adb) or (str(pathlib.Path(args.adb).resolve()) if pathlib.Path(args.adb).is_file() else None)
if not adb:
    raise SystemExit("adb executable not found")
def run(*values, check=True):
    result = subprocess.run([adb, "-s", args.serial, *values], text=True, encoding="utf-8", errors="replace", capture_output=True)
    if check and result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"adb failed: {result.returncode}")
    return result
def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
def snapshot():
    paths_result = run("shell", "pm", "path", PACKAGE, check=False)
    paths = [line.removeprefix("package:").strip() for line in paths_result.stdout.splitlines() if line.startswith("package:")]
    if not paths:
        return {"installed": False, "versionName": None, "versionCode": None}
    dump = run("shell", "dumpsys", "package", PACKAGE).stdout
    name = re.search(r"^\s*versionName=([^\s]+)", dump, re.MULTILINE)
    code = re.search(r"^\s*versionCode=(\d+)", dump, re.MULTILINE)
    return {"installed": True, "versionName": name.group(1) if name else None, "versionCode": code.group(1) if code else None}
current = snapshot()
target = before["input"]
if current["installed"]:
    if target.get("version_name") and current["versionName"] != target["version_name"]:
        raise SystemExit("Current package version drifted after installation; refusing rollback")
    if target.get("version_code") and current["versionCode"] != target["version_code"]:
        raise SystemExit("Current package version drifted after installation; refusing rollback")
elif before["package"]["installed"]:
    raise SystemExit("Current package is absent; refusing to overwrite the changed device state")
uid = run("shell", "id", "-u").stdout.strip()
if uid == "0":
    run("unroot")
    run("wait-for-device")
package = before["package"]
try:
    if package["installed"]:
        backup = root / "previous-apks"
        files = sorted(backup.glob("*.apk"))
        records = json.loads((root / "previous-apks.json").read_text(encoding="utf-8-sig"))
        expected = {path.rsplit("/", 1)[-1] for path in package["apkPaths"]}
        if {path.name for path in files} != expected or {record["fileName"] for record in records} != expected:
            raise SystemExit("Previous APK backup is incomplete; nothing was changed")
        expected_hashes = {record["fileName"]: record["sha256"] for record in records}
        if any(sha256(path) != expected_hashes[path.name] for path in files):
            raise SystemExit("Previous APK backup hash mismatch; nothing was changed")
        command = ["install-multiple", "-r", "-d"]
        if package.get("installerPackageName"):
            command += ["-i", package["installerPackageName"]]
        command += [str(path) for path in files]
        result = run(*command)
        if "success" not in result.stdout.lower():
            raise SystemExit("Previous APK reinstall did not report Success")
    elif current["installed"]:
        run("uninstall", PACKAGE)
    restored = snapshot()
    if package["installed"]:
        if not restored["installed"] or restored["versionName"] != package["versionName"] or restored["versionCode"] != package["versionCode"]:
            raise SystemExit("Rollback package version verification failed")
    elif restored["installed"]:
        raise SystemExit("Rollback removal verification failed")
finally:
    if before["adbdWasRoot"]:
        run("root")
        run("wait-for-device")
print("Rollback completed")
'''


def write_rollback(state_directory: Path) -> Path:
    path = state_directory / "rollback.py"
    path.write_text(ROLLBACK_SCRIPT, encoding="utf-8", newline="\n")
    with contextlib.suppress(OSError):
        path.chmod(0o755)
    return path


def verify_installed_snapshot(after: dict[str, Any], xapk: XapkIdentity) -> None:
    if not after["installed"]:
        raise ToolError(f"{PACKAGE_NAME} is absent after installation")
    if after["installerPackageName"] != INSTALLER_PACKAGE:
        raise ToolError(
            f"Installer verification failed: {after['installerPackageName']!r}; expected {INSTALLER_PACKAGE!r}"
        )
    leaves = {path.rsplit("/", 1)[-1] for path in after["apkPaths"]}
    expected = set(ROLE_FILENAMES.values())
    if leaves != expected:
        raise ToolError(f"Installed split verification failed: {sorted(leaves)}")
    if xapk.version_name and after["versionName"] != xapk.version_name:
        raise ToolError(f"Installed versionName {after['versionName']!r} does not match {xapk.version_name!r}")
    if xapk.version_code and after["versionCode"] != xapk.version_code:
        raise ToolError(f"Installed versionCode {after['versionCode']!r} does not match {xapk.version_code!r}")


def launch_and_verify(adb: AdbRunner, wait_seconds: float) -> dict[str, Any]:
    launched = adb.run(
        ["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"]
    )
    if re.search(r"no activities found|aborted", launched.stdout, re.IGNORECASE):
        raise ToolError("Launcher Activity did not start")
    time.sleep(wait_seconds)
    pid_result = adb.run(["shell", "pidof", PACKAGE_NAME], check=False)
    activity_result = adb.run(["shell", "dumpsys", "activity", "activities"], check=False)
    resumed = next(
        (
            line.strip()
            for line in activity_result.stdout.splitlines()
            if "mResumedActivity" in line or "topResumedActivity" in line
        ),
        None,
    )
    if resumed and "com.android.vending" in resumed:
        raise ToolError(f"Google Play resumed instead of the game: {resumed}")
    process_alive = pid_result.returncode == 0 and bool(pid_result.stdout.strip())
    if not process_alive and (not resumed or PACKAGE_NAME not in resumed):
        raise ToolError("The game process/Activity was not observable after launch")
    return {"attempted": True, "processAlive": process_alive, "resumedActivity": resumed}


def install_xapk(
    xapk: XapkIdentity,
    state_directory: Path,
    *,
    serial: str,
    adb_executable: str,
    launch: bool,
    launch_wait: float,
    skip_backup: bool,
    restore_root: bool,
) -> dict[str, Any]:
    operation_log = state_directory / "adb-operations.jsonl"
    adb = AdbRunner(adb_executable, serial, operation_log)
    switched_from_root = False
    root_restored = False
    before_record_written = False
    rollback_available = False
    journal_path = state_directory / "journal.json"
    def journal(stage: str) -> None:
        atomic_write_json(journal_path, {"stage": stage, "updatedAt": utc_now()})
    try:
        state_result = adb.run(["get-state"])
        if "device" not in state_result.stdout:
            raise ToolError(f"ADB device is not ready: {state_result.stdout.strip()}")
        uid = adb.run(["shell", "id", "-u"]).stdout.strip()
        adbd_was_root = uid == "0"
        before = package_snapshot(adb)
        before_record = {
            "createdAt": utc_now(),
            "serial": serial,
            "adbdWasRoot": adbd_was_root,
            "package": before,
            "input": dataclasses.asdict(xapk),
            "rollbackAvailable": not before["installed"] or not skip_backup,
        }
        atomic_write_json(state_directory / "before.json", before_record)
        before_record_written = True
        journal("prepared")
        if before["installed"] and not skip_backup:
            backup_records = backup_current_apks(adb, before, state_directory / "previous-apks")
            atomic_write_json(state_directory / "previous-apks.json", backup_records)
            rollback_available = True
            write_rollback(state_directory)
            journal("backed-up")
        elif before["installed"]:
            atomic_write_json(
                state_directory / "previous-apks.json",
                {"skipped": True, "warning": "Exact APK rollback is unavailable"},
            )
        else:
            rollback_available = True
            write_rollback(state_directory)
            journal("backed-up")

        if adbd_was_root:
            adb.run(["unroot"])
            adb.run(["wait-for-device"])
            switched_from_root = True

        apk_paths = [apk.path for apk in xapk.apks]
        result = adb.run(["install-multiple", "-r", "-i", INSTALLER_PACKAGE, *apk_paths])
        if "success" not in result.stdout.lower():
            raise ToolError(f"Package Installer did not report Success: {result.stdout.strip()}")
        journal("install-committed")

        if switched_from_root and restore_root:
            adb.run(["root"])
            adb.run(["wait-for-device"])
            root_restored = True
        after = package_snapshot(adb)
        verify_installed_snapshot(after, xapk)
        launch_record = {"attempted": False, "processAlive": None, "resumedActivity": None}
        if launch:
            launch_record = launch_and_verify(adb, launch_wait)
        verification = {
            "verifiedAt": utc_now(),
            "status": "verified",
            "mode": "update" if before["installed"] else "fresh-install",
            "package": after,
            "requiredInstaller": INSTALLER_PACKAGE,
            "requiredSplits": list(ROLE_FILENAMES.values()),
            "launch": launch_record,
            "rollbackAvailable": rollback_available,
            "rollback": str((state_directory / "rollback.py").resolve()) if rollback_available else None,
        }
        atomic_write_json(state_directory / "verification.json", verification)
        journal("verified")
        return verification
    except Exception as error:
        atomic_write_json(
            state_directory / "failure.json",
            {
                "failedAt": utc_now(),
                "errorType": type(error).__name__,
                "message": str(error),
                "rollbackAvailable": rollback_available,
                "rollback": str((state_directory / "rollback.py").resolve()) if rollback_available else None,
            },
        )
        raise
    finally:
        if switched_from_root and restore_root and not root_restored:
            with contextlib.suppress(Exception):
                adb.run(["root"], check=False)
                adb.run(["wait-for-device"], check=False)


def default_data_root() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "MagiaExedraTWTools"
    return Path.home() / ".local" / "state" / "MagiaExedraTWTools"


def new_state_directory(parent: Path | None) -> Path:
    root = parent or (default_data_root() / "install-state")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = root / f"{stamp}-{os.getpid()}"
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or update the unmodified Magia Exedra Taiwan XAPK on MuMu/ADB"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--xapk", type=Path, help="local original XAPK")
    source.add_argument(
        "--download-latest",
        action="store_true",
        help="download the release selected by manifests/known-releases.json",
    )
    parser.add_argument("--serial", help="ADB serial (required unless --validate-only)")
    parser.add_argument("--adb", default="adb", help="adb executable or path")
    parser.add_argument("--proxy", help="optional HTTP/HTTPS proxy URL used only for XAPK download")
    parser.add_argument("--download-dir", type=Path, help="download cache directory")
    parser.add_argument("--download-url", help=argparse.SUPPRESS)
    parser.add_argument(
        "--release-manifest",
        type=Path,
        default=DEFAULT_RELEASE_MANIFEST,
        help="trusted release manifest (default: repository known-releases.json)",
    )
    parser.add_argument(
        "--expected-xapk-sha256",
        help="required separately trusted SHA-256 only for a local version absent from the release manifest",
    )
    parser.add_argument("--state-parent", type=Path, help="parent directory for evidence/checkpoints")
    parser.add_argument("--validate-only", action="store_true", help="validate XAPK without ADB")
    parser.add_argument("--launch", action="store_true", help="explicitly launch after verification")
    parser.add_argument("--launch-wait", type=float, default=3.0, help=argparse.SUPPRESS)
    parser.add_argument("--skip-current-apk-backup", action="store_true")
    parser.add_argument("--no-restore-adb-root", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if not arguments.validate_only and not arguments.serial:
        parser.error("--serial is required for install/update")
    release_manifest = load_release_manifest(arguments.release_manifest)
    expected_hash = (
        normalize_sha256(arguments.expected_xapk_sha256, "--expected-xapk-sha256")
        if arguments.expected_xapk_sha256
        else None
    )
    download_record: DownloadResult | None = None
    if arguments.download_latest:
        if expected_hash is not None:
            raise ToolError(
                "--expected-xapk-sha256 cannot override --download-latest; update the trusted release manifest"
            )
        latest = release_manifest.latest
        download_directory = arguments.download_dir or (default_data_root() / "downloads")
        xapk_path = download_directory / f"{PACKAGE_NAME}-latest.xapk"
        download_record = download_file(
            arguments.download_url or release_manifest.latest_endpoint,
            xapk_path,
            proxy=arguments.proxy,
            expected_sha256=latest.xapk.sha256,
            expected_size=latest.xapk.length,
        )
    else:
        xapk_path = arguments.xapk
        assert xapk_path is not None
        if not xapk_path.is_file():
            raise ToolError(f"XAPK not found: {xapk_path}")

    if arguments.validate_only:
        with tempfile.TemporaryDirectory(prefix="tw-xapk-validate-") as temporary:
            identity = extract_and_validate_xapk(xapk_path, Path(temporary))
            trusted_release = enforce_xapk_trust(
                identity,
                release_manifest,
                expected_hash,
                require_latest=arguments.download_latest,
            )
        output = {
            "status": "validated",
            "releaseManifest": release_manifest.path,
            "trust": {
                "knownRelease": trusted_release.version_name if trusted_release else None,
                "externalSha256": expected_hash if trusted_release is None else None,
            },
            "xapk": dataclasses.asdict(identity),
        }
        if download_record:
            output["download"] = dataclasses.asdict(download_record)
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    state_directory = new_state_directory(arguments.state_parent)
    try:
        identity = extract_and_validate_xapk(xapk_path, state_directory / "input-apks")
        trusted_release = enforce_xapk_trust(
            identity,
            release_manifest,
            expected_hash,
            require_latest=arguments.download_latest,
        )
        input_record: dict[str, Any] = {
            "releaseManifest": release_manifest.path,
            "trustedKnownRelease": trusted_release.version_name if trusted_release else None,
            "externalSha256": expected_hash if trusted_release is None else None,
            "xapk": dataclasses.asdict(identity),
        }
        if download_record:
            input_record["download"] = dataclasses.asdict(download_record)
        atomic_write_json(state_directory / "input.json", input_record)
        verification = install_xapk(
            identity,
            state_directory,
            serial=arguments.serial,
            adb_executable=arguments.adb,
            launch=arguments.launch,
            launch_wait=max(0.0, arguments.launch_wait),
            skip_backup=arguments.skip_current_apk_backup,
            restore_root=not arguments.no_restore_adb_root,
        )
    except Exception:
        print(f"State/evidence directory: {state_directory}", file=sys.stderr)
        raise
    print(json.dumps({"stateDirectory": str(state_directory.resolve()), **verification}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ToolError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
