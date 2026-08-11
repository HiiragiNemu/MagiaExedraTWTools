from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


installer = _load_module(
    "tw_original_installer_public_defaults_under_test",
    ROOT / "tools" / "tw_original_installer.py",
)

@pytest.mark.parametrize("proxy", [None, ""])
def test_installer_empty_proxy_is_explicit_direct_mode(proxy: str | None) -> None:
    captured: list[object] = []

    def fake_build_opener(*handlers):
        captured.extend(handlers)
        return SimpleNamespace(handlers=handlers)

    with mock.patch.object(installer.urllib.request, "build_opener", side_effect=fake_build_opener):
        result = installer._build_opener(proxy)

    assert result.handlers == tuple(captured)
    assert len(captured) == 1
    assert isinstance(captured[0], installer.urllib.request.ProxyHandler)
    assert captured[0].proxies == {}


def test_installer_uses_only_explicit_proxy() -> None:
    captured: list[object] = []

    def fake_build_opener(*handlers):
        captured.extend(handlers)
        return SimpleNamespace(handlers=handlers)

    proxy = "http://127.0.0.1:12345"
    with mock.patch.object(installer.urllib.request, "build_opener", side_effect=fake_build_opener):
        installer._build_opener(proxy)

    assert len(captured) == 1
    assert captured[0].proxies == {"http": proxy, "https": proxy}


def test_product_defaults_do_not_hardcode_private_proxy_port() -> None:
    product_files = [
        ROOT / "install_tw.py",
        ROOT / "tools" / "tw_original_installer.py",
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*.md")),
        *sorted((ROOT / "mobile").glob("*")),
    ]
    offenders = [
        str(path.relative_to(ROOT))
        for path in product_files
        if path.is_file() and "127.0.0.1:7897" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_mobile_script_pins_all_hashes_and_never_launches() -> None:
    script = (ROOT / "mobile" / "install_tw_termux.sh").read_text(encoding="utf-8")
    checksums = (ROOT / "mobile" / "SHA256SUMS-tw-1.1.2.txt").read_text(encoding="utf-8")
    expected = {
        "664dfbc307c5f6b640d01b1fc661de02fa30fc382a68426530abc657dc9e2d14",
        "ceafa5ba761b8d3996ce2718ff163b8b21707fdc1d304d6edc27b8582c93038e",
        "0d21a05fd1007b31a1a6fa72561c6d6f2eeaa8353492913dd925465bc10d82ed",
        "19466690a93ae7ea84485b86453901c5ed7745aea2b2d0cd4098bb13b02c69c5",
    }
    assert all(digest in script for digest in expected)
    assert all(digest in checksums for digest in expected)
    assert 'install-multiple -r -i "$INSTALLER_PACKAGE"' in script
    assert 'shell am force-stop "$PACKAGE_NAME"' in script
    lowered = script.lower()
    assert "am start" not in lowered
    assert "monkey" not in lowered
    assert "--launch" not in lowered


def test_mobile_docs_cover_both_supported_routes_and_boundary() -> None:
    for name in ("TW_ANDROID_PHONE_INSTALL.zh-CN.md", "TW_ANDROID_PHONE_INSTALL.en.md"):
        content = (ROOT / "docs" / name).read_text(encoding="utf-8")
        assert "https://shizuku.rikka.app/download/" in content
        assert "https://github.com/zacharee/InstallWithOptions" in content
        assert "https://termux.dev/en/" in content
        assert "com.android.vending" in content
        assert "664dfbc307c5f6b640d01b1fc661de02fa30fc382a68426530abc657dc9e2d14" in content
        assert "Android 11" in content
        assert "Android 10" in content


def test_mobile_shell_script_parses() -> None:
    bundled_git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    bash = str(bundled_git_bash) if bundled_git_bash.is_file() else shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available on this host")
    completed = subprocess.run(
        [bash, "-n", str(ROOT / "mobile" / "install_tw_termux.sh")],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0, completed.stderr
