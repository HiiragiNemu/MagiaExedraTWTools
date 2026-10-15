import copy
import importlib.util
import io
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('jp_health', ROOT / 'scripts/check_jp_release.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)
MANIFEST = json.loads((ROOT / 'manifests/jp-known-releases.json').read_text())


class Response(io.BytesIO):
    status = 200


class Opener:
    def __init__(self, assets):
        self.assets = assets
    def open(self, request, **kwargs):
        if request.get_method() == 'HEAD':
            r = Response()
            r.headers = {'Content-Length': str(MANIFEST['releases'][0]['length'])}
            return r
        return Response(json.dumps({'assets': self.assets}).encode())


def asset():
    release = MANIFEST['releases'][0]
    return {'name': MANIFEST['latestEndpoint'].split('/')[-1], 'size': release['length'],
            'digest': 'sha256:' + release['sha256']}


def test_published_pin():
    assert health.check(MANIFEST, Opener([asset()]))['ok']


def test_empty_release_rejected():
    with pytest.raises(ValueError, match='no matching'):
        health.check(MANIFEST, Opener([]))


def test_wrong_hash_rejected():
    a = asset(); a['digest'] = 'sha256:' + '0' * 64
    with pytest.raises(ValueError, match='differs'):
        health.check(MANIFEST, Opener([a]))


def test_mutable_latest_rejected():
    m = copy.deepcopy(MANIFEST); m['latestEndpoint'] = 'https://example.com/latest'
    with pytest.raises(ValueError, match='fixed GitHub'):
        health.check(m, Opener([asset()]))


def test_docs_and_checksums_are_current():
    version = MANIFEST['latestVersion']
    evidence = json.loads((ROOT / f'docs/JP_CLIENT_{version}_VERIFICATION.json').read_text())
    assert evidence['xapk']['sha256'] == MANIFEST['releases'][0]['sha256']
    assert version in (ROOT / 'docs/JP_ANDROID_INSTALL.zh-CN.md').read_text(encoding='utf-8')
    assert MANIFEST['releases'][0]['sha256'] in (ROOT / f'mobile/SHA256SUMS-jp-{version}.txt').read_text()
