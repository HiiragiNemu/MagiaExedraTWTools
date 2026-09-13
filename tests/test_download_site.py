import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def test_site_build_uses_latest_manifest_and_public_release_links(tmp_path):
    spec=importlib.util.spec_from_file_location('site_builder',ROOT/'scripts/build_site.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    builder.build(tmp_path/'site')
    page=(tmp_path/'site/index.html').read_text(encoding='utf-8')
    manifest=json.loads((ROOT/'manifests/known-releases.json').read_text(encoding='utf-8'))
    jp_manifest=json.loads((ROOT/'manifests/jp-known-releases.json').read_text(encoding='utf-8'))
    latest=next(r for r in manifest['releases'] if r['versionName']==manifest['latestVersion'])
    assert '{{' not in page
    assert manifest['latestEndpoint'] in page
    assert latest['sha256'] in page
    jp_latest=next(row for row in jp_manifest['releases'] if row['versionName']==jp_manifest['latestVersion'])
    assert jp_manifest['latestEndpoint'] in page
    assert jp_latest['sha256'] in page
    assert f"JP {jp_latest['versionName']}" in page
    assert f"{latest['length']/1048576:.1f} MiB" in page
    assert 'com.android.vending' in page
    assert '不要先卸载' in page
    assert '实际登录验收' in page
    assert 'lang="zh-CN"' in page
    ids=set(re.findall(r'\bid="([^"]+)"',page))
    for target in re.findall(r'href="#([^"]+)"',page):assert target in ids
    for href in re.findall(r'(?:href|src)="([^"]+)"',page):
        if href.startswith(('https://','#')):continue
        assert (tmp_path/'site'/href).is_file(),href
    assert not list((tmp_path/'site').rglob('*.xapk'))
    assert max(p.stat().st_size for p in (tmp_path/'site').rglob('*') if p.is_file())<25*1024*1024

def test_site_keyboard_tabs_and_copy_controls_have_targets():
    page=(ROOT/'site/index.html').read_text(encoding='utf-8')
    ids=set(re.findall(r'\bid="([^"]+)"',page))
    for target in re.findall(r'(?:aria-controls|data-copy)="([^"]+)"',page):assert target in ids
    js=(ROOT/'site/site.js').read_text(encoding='utf-8')
    assert all(key in js for key in ['ArrowLeft','ArrowRight','Home','End'])
    assert 'navigator.clipboard.writeText' in js
