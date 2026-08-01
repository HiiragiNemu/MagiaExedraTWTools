from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "tw_original_installer.py"
SPEC = importlib.util.spec_from_file_location("tw_original_installer", MODULE_PATH)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = installer
SPEC.loader.exec_module(installer)


def _apk_bytes(package: str, split: str, version_name: str, version_code: str) -> bytes:
    split_attribute = f' split="{split}"' if split else ""
    manifest = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
        f'package="{package}"{split_attribute} '
        f'android:versionName="{version_name}" android:versionCode="{version_code}">'
        '<application /></manifest>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("AndroidManifest.xml", manifest)
    return buffer.getvalue()


def _write_xapk(path: Path, version_name: str = "1.1.2", version_code: str = "26072717") -> None:
    package = "tw.sonet.magiaexedra"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "package_name": package,
                    "version_name": version_name,
                    "version_code": version_code,
                }
            ),
        )
        archive.writestr("tw.sonet.magiaexedra.apk", _apk_bytes(package, "", version_name, version_code))
        archive.writestr("base_assets.apk", _apk_bytes(package, "base_assets", version_name, version_code))
        archive.writestr(
            "config.arm64_v8a.apk",
            _apk_bytes(package, "config.arm64_v8a", version_name, version_code),
        )


def _write_release_manifest(path: Path, xapk: Path, latest_endpoint: str = "https://example.invalid/latest.xapk") -> None:
    with tempfile.TemporaryDirectory() as temporary:
        identity = installer.extract_and_validate_xapk(xapk, Path(temporary))
    splits = {
        apk.split or "base": {"length": apk.length, "sha256": apk.sha256}
        for apk in identity.apks
    }
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "packageName": "tw.sonet.magiaexedra",
                "latestVersion": identity.version_name,
                "latestEndpoint": latest_endpoint,
                "releases": [
                    {
                        "versionName": identity.version_name,
                        "versionCode": int(identity.version_code),
                        "length": identity.length,
                        "sha256": identity.sha256,
                        "splits": splits,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_fake_adb(root: Path) -> Path:
    implementation = root / "fake_adb_cli.py"
    implementation.write_text(
        r'''from __future__ import annotations
import io, json, os, pathlib, sys, zipfile

state_path = pathlib.Path(os.environ["FAKE_ADB_STATE"])
log_path = pathlib.Path(os.environ["FAKE_ADB_LOG"])
state = json.loads(state_path.read_text(encoding="utf-8"))
args = sys.argv[1:]
if len(args) >= 2 and args[0] == "-s":
    args = args[2:]
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\n")
def save():
    state_path.write_text(json.dumps(state), encoding="utf-8")
if args == ["get-state"]:
    print("device")
elif args == ["shell", "id", "-u"]:
    print(state["uid"])
elif args[:4] == ["shell", "pm", "path", "tw.sonet.magiaexedra"]:
    if state["installed"]:
        for name in ("base.apk", "split_base_assets.apk", "split_config.arm64_v8a.apk"):
            print(f"package:/data/app/example/{name}")
elif args[:3] == ["shell", "dumpsys", "package"]:
    if state["installed"]:
        print(f"versionCode={state['versionCode']} minSdk=23")
        print(f"versionName={state['versionName']}")
        print(f"installerPackageName={state.get('installer') or 'null'}")
elif args[:5] == ["shell", "cmd", "package", "get-install-source", "tw.sonet.magiaexedra"]:
    print(f"Installer package name: {state.get('installer') or 'null'}")
elif args and args[0] == "pull":
    destination = pathlib.Path(args[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    name = destination.name
    split = {"base.apk": "", "split_base_assets.apk": "base_assets", "split_config.arm64_v8a.apk": "config.arm64_v8a"}[name]
    split_attribute = f' split="{split}"' if split else ""
    manifest = ('<?xml version="1.0" encoding="utf-8"?>'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="tw.sonet.magiaexedra"'
        + split_attribute + f' android:versionName="{state["versionName"]}" android:versionCode="{state["versionCode"]}"><application /></manifest>')
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("AndroidManifest.xml", manifest)
    print("1 file pulled")
elif args == ["unroot"]:
    state["uid"] = "2000"; save(); print("restarting adbd as non root")
elif args == ["root"]:
    state["uid"] = "0"; save(); print("restarting adbd as root")
elif args == ["wait-for-device"]:
    pass
elif args and args[0] == "install-multiple":
    restoring = any("previous-apks" in value for value in args)
    state["installed"] = True
    if restoring:
        state["versionName"] = state["previousVersionName"]
        state["versionCode"] = state["previousVersionCode"]
    else:
        state["versionName"] = state["targetVersionName"]
        state["versionCode"] = state["targetVersionCode"]
    state["installer"] = args[args.index("-i") + 1] if "-i" in args else None
    save(); print("Success")
elif args == ["uninstall", "tw.sonet.magiaexedra"]:
    state["installed"] = False; state["installer"] = None; save(); print("Success")
elif args[:2] == ["shell", "monkey"]:
    print("Events injected: 1")
elif args[:3] == ["shell", "pidof", "tw.sonet.magiaexedra"]:
    print("1234")
elif args[:4] == ["shell", "dumpsys", "activity", "activities"]:
    print("mResumedActivity: tw.sonet.magiaexedra/.MainActivity")
else:
    print("unhandled fake adb arguments: " + repr(args), file=sys.stderr)
    raise SystemExit(2)
''',
        encoding="utf-8",
    )
    if os.name == "nt":
        launcher = root / "adb.cmd"
        launcher.write_text(
            f'@echo off\r\n"{sys.executable}" "{implementation}" %*\r\n', encoding="utf-8"
        )
    else:
        launcher = root / "adb"
        launcher.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{implementation}" "$@"\n', encoding="utf-8"
        )
        launcher.chmod(0o755)
    return launcher


def _run_cli(
    root: Path, installed: bool, extra_arguments: tuple[str, ...] = ()
) -> tuple[subprocess.CompletedProcess[str], Path, dict, list[list[str]]]:
    xapk = root / "client.xapk"
    _write_xapk(xapk)
    release_manifest = root / "known-releases.json"
    _write_release_manifest(release_manifest, xapk)
    adb = _write_fake_adb(root)
    state_path = root / "device-state.json"
    log_path = root / "adb.log"
    state = {
        "uid": "0",
        "installed": installed,
        "installer": None,
        "versionName": "1.0.5" if installed else None,
        "versionCode": "26032510" if installed else None,
        "previousVersionName": "1.0.5",
        "previousVersionCode": "26032510",
        "targetVersionName": "1.1.2",
        "targetVersionCode": "26072717",
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    environment = os.environ.copy()
    environment.update(FAKE_ADB_STATE=str(state_path), FAKE_ADB_LOG=str(log_path))
    state_parent = root / "states"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "--xapk",
        str(xapk),
        "--serial",
        "offline:1",
        "--adb",
        str(adb),
        "--state-parent",
        str(state_parent),
        "--release-manifest",
        str(release_manifest),
        *extra_arguments,
    ]
    result = subprocess.run(
        command, text=True, encoding="utf-8", errors="replace", capture_output=True, env=environment
    )
    checkpoints = list(state_parent.glob("*"))
    checkpoint = checkpoints[0] if len(checkpoints) == 1 else state_parent
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    return result, checkpoint, final_state, calls


class _RangeHandler(BaseHTTPRequestHandler):
    payload = b""
    ranges: list[str | None] = []
    send_content_length = True

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        requested = self.headers.get("Range")
        type(self).ranges.append(requested)
        start = 0
        status = 200
        if requested:
            start = int(requested.removeprefix("bytes=").removesuffix("-"))
            status = 206
        body = type(self).payload[start:]
        self.send_response(status)
        if type(self).send_content_length:
            self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", '"offline-fixture"')
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{len(type(self).payload)-1}/{len(type(self).payload)}")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


class TwInstallerCliTest(unittest.TestCase):
    def test_public_tree_is_python_only(self) -> None:
        self.assertEqual(list(ROOT.rglob("*.ps1")), [])
        for path in (ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))):
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("powershell", text)

    def test_python_xapk_validation_rejects_wrong_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            xapk = root / "wrong.xapk"
            with zipfile.ZipFile(xapk, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps({"package_name": "example.wrong", "version_name": "1", "version_code": "1"}),
                )
                archive.writestr("base.apk", _apk_bytes("example.wrong", "", "1", "1"))
                archive.writestr("assets.apk", _apk_bytes("example.wrong", "base_assets", "1", "1"))
                archive.writestr("abi.apk", _apk_bytes("example.wrong", "config.arm64_v8a", "1", "1"))
            with tempfile.TemporaryDirectory() as output:
                with self.assertRaises(installer.ToolError):
                    installer.extract_and_validate_xapk(xapk, Path(output))

    def test_fresh_install_defaults_to_no_launch_and_rolls_back_to_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, checkpoint, state, calls = _run_cli(root, installed=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads((checkpoint / "verification.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["mode"], "fresh-install")
            self.assertFalse(evidence["launch"]["attempted"])
            self.assertTrue(state["installed"])
            self.assertFalse(any(call[:2] == ["shell", "monkey"] for call in calls))

            environment = os.environ.copy()
            environment.update(
                FAKE_ADB_STATE=str(root / "device-state.json"), FAKE_ADB_LOG=str(root / "adb.log")
            )
            rollback = subprocess.run(
                [sys.executable, str(checkpoint / "rollback.py"), "--adb", str(root / ("adb.cmd" if os.name == "nt" else "adb"))],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=environment,
            )
            self.assertEqual(rollback.returncode, 0, rollback.stdout + rollback.stderr)
            restored = json.loads((root / "device-state.json").read_text(encoding="utf-8"))
            self.assertFalse(restored["installed"])

    def test_update_backs_up_old_splits_and_rollback_restores_old_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, checkpoint, state, calls = _run_cli(root, installed=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(state["versionName"], "1.1.2")
            self.assertEqual(len(list((checkpoint / "previous-apks").glob("*.apk"))), 3)
            install = next(call for call in calls if call[:1] == ["install-multiple"])
            self.assertEqual(install[1:4], ["-r", "-i", "com.android.vending"])
            self.assertFalse(any(call[:2] == ["shell", "monkey"] for call in calls))

            environment = os.environ.copy()
            environment.update(
                FAKE_ADB_STATE=str(root / "device-state.json"), FAKE_ADB_LOG=str(root / "adb.log")
            )
            adb = root / ("adb.cmd" if os.name == "nt" else "adb")
            rollback = subprocess.run(
                [sys.executable, str(checkpoint / "rollback.py"), "--adb", str(adb)],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=environment,
            )
            self.assertEqual(rollback.returncode, 0, rollback.stdout + rollback.stderr)
            restored = json.loads((root / "device-state.json").read_text(encoding="utf-8"))
            self.assertTrue(restored["installed"])
            self.assertEqual(restored["versionName"], "1.0.5")
            self.assertIsNone(restored["installer"])

    def test_explicit_backup_skip_never_claims_runnable_update_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, checkpoint, _, _ = _run_cli(
                root, installed=True, extra_arguments=("--skip-current-apk-backup",)
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads((checkpoint / "verification.json").read_text(encoding="utf-8"))
            self.assertFalse(evidence["rollbackAvailable"])
            self.assertIsNone(evidence["rollback"])
            self.assertFalse((checkpoint / "rollback.py").exists())

    def test_download_latest_cli_resumes_and_atomically_validates_fake_xapk(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.xapk"
            _write_xapk(source)
            release_manifest = root / "known-releases.json"
            _write_release_manifest(release_manifest, source)
            payload = source.read_bytes()
            _RangeHandler.payload = payload
            _RangeHandler.ranges = []
            _RangeHandler.send_content_length = True
            server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/latest.xapk"
                download_dir = root / "downloads"
                download_dir.mkdir()
                final = download_dir / "tw.sonet.magiaexedra-latest.xapk"
                partial = final.with_name(final.name + ".part")
                prefix_length = len(payload) // 3
                partial.write_bytes(payload[:prefix_length])
                installer.atomic_write_json(
                    final.with_name(final.name + ".part.json"),
                    {"url": installer.sanitized_url(url), "etag": '"offline-fixture"'},
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = installer.main(
                        [
                            "--download-latest",
                            "--download-url",
                            url,
                            "--download-dir",
                            str(download_dir),
                            "--release-manifest",
                            str(release_manifest),
                            "--validate-only",
                        ]
                    )
                self.assertEqual(exit_code, 0)
                self.assertEqual(final.read_bytes(), payload)
                self.assertFalse(partial.exists())
                self.assertIn(f"bytes={prefix_length}-", _RangeHandler.ranges)
                report = json.loads(output.getvalue())
                self.assertEqual(report["download"]["resumed_from"], prefix_length)
                self.assertEqual(report["status"], "validated")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_known_release_manifest_matches_pinned_latest(self) -> None:
        raw = json.loads((ROOT / "manifests" / "known-releases.json").read_text(encoding="utf-8"))
        manifest = installer.load_release_manifest()
        latest = manifest.latest
        self.assertEqual(manifest.latest_version, raw["latestVersion"])
        self.assertEqual(latest.version_name, raw["latestVersion"])
        self.assertEqual(latest.xapk.sha256, next(
            release["sha256"] for release in raw["releases"] if release["versionName"] == raw["latestVersion"]
        ))
        self.assertEqual(set(latest.splits), {"base", "base_assets", "config.arm64_v8a"})
        self.assertEqual(
            latest.splits["base"].sha256,
            "ceafa5ba761b8d3996ce2718ff163b8b21707fdc1d304d6edc27b8582c93038e",
        )
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(latest.xapk.sha256, source)
        self.assertNotIn("KNOWN_LATEST", source)

    def test_latest_selection_is_driven_by_manifest_field_not_array_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "releases.json"
            raw = json.loads((ROOT / "manifests" / "known-releases.json").read_text(encoding="utf-8"))
            raw["latestVersion"] = "1.0.5"
            path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = installer.load_release_manifest(path)
            self.assertEqual(loaded.latest.version_name, "1.0.5")
            self.assertEqual(loaded.latest.version_code, "26032510")

    def test_known_local_release_rejects_outer_xapk_hash_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            xapk = root / "known.xapk"
            manifest_path = root / "releases.json"
            _write_xapk(xapk)
            _write_release_manifest(manifest_path, xapk)
            with zipfile.ZipFile(xapk, "a", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("outer-container-tamper.txt", "changed after trust manifest")
            with self.assertRaisesRegex(installer.ToolError, "Known release XAPK length/SHA-256 mismatch"):
                installer.main(
                    [
                        "--xapk",
                        str(xapk),
                        "--release-manifest",
                        str(manifest_path),
                        "--validate-only",
                    ]
                )
            with self.assertRaisesRegex(installer.ToolError, "cannot override"):
                installer.main(
                    [
                        "--xapk",
                        str(xapk),
                        "--release-manifest",
                        str(manifest_path),
                        "--expected-xapk-sha256",
                        hashlib.sha256(xapk.read_bytes()).hexdigest(),
                        "--validate-only",
                    ]
                )

    def test_known_release_enforces_each_split_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            xapk = root / "known.xapk"
            manifest_path = root / "releases.json"
            _write_xapk(xapk)
            _write_release_manifest(manifest_path, xapk)
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw["releases"][0]["splits"]["base"]["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(installer.ToolError, "split base length/SHA-256 mismatch"):
                installer.main(
                    [
                        "--xapk",
                        str(xapk),
                        "--release-manifest",
                        str(manifest_path),
                        "--validate-only",
                    ]
                )

    def test_unknown_local_release_requires_separately_trusted_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            known = root / "known.xapk"
            unknown = root / "unknown.xapk"
            manifest_path = root / "releases.json"
            _write_xapk(known)
            _write_release_manifest(manifest_path, known)
            _write_xapk(unknown, version_name="9.9.9", version_code="99999999")
            with self.assertRaisesRegex(installer.ToolError, "Unknown XAPK version"):
                installer.main(
                    [
                        "--xapk",
                        str(unknown),
                        "--release-manifest",
                        str(manifest_path),
                        "--validate-only",
                    ]
                )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = installer.main(
                    [
                        "--xapk",
                        str(unknown),
                        "--release-manifest",
                        str(manifest_path),
                        "--expected-xapk-sha256",
                        hashlib.sha256(unknown.read_bytes()).hexdigest(),
                        "--validate-only",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertIsNone(json.loads(output.getvalue())["trust"]["knownRelease"])

    def test_download_without_content_length_uses_expected_size_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b"stream-without-content-length"
            _RangeHandler.payload = payload
            _RangeHandler.ranges = []
            _RangeHandler.send_content_length = False
            server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = installer.download_file(
                    f"http://127.0.0.1:{server.server_port}/payload",
                    root / "payload.xapk",
                    expected_size=len(payload),
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                )
                self.assertEqual(result.length, len(payload))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_download_rejects_stream_over_expected_and_global_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b"x" * 65
            _RangeHandler.payload = payload
            _RangeHandler.ranges = []
            _RangeHandler.send_content_length = False
            server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/payload"
                with self.assertRaisesRegex(installer.ToolError, "trusted limit"):
                    installer.download_file(url, root / "over-expected.xapk", expected_size=32)
                with mock.patch.object(installer, "MAX_DOWNLOAD_BYTES", 64):
                    with self.assertRaisesRegex(installer.ToolError, "trusted limit"):
                        installer.download_file(url, root / "over-global.xapk")
                    with self.assertRaisesRegex(installer.ToolError, "safety limit"):
                        installer.download_file(url, root / "impossible.xapk", expected_size=65)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
