"""Manually verify the published JP pin and anonymous download (no ADB)."""
import argparse
import json
from pathlib import Path
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def check(manifest, opener=None):
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    release = next(r for r in manifest['releases'] if r['versionName'] == manifest['latestVersion'])
    url = manifest['latestEndpoint']
    parsed = urlparse(url)
    prefix = '/HiiragiNemu/MagiaExedraTWTools/releases/download/'
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or not parsed.path.startswith(prefix):
        raise ValueError('Expected a fixed GitHub release URL, not a mutable latest endpoint')
    tag, filename = parsed.path[len(prefix):].split('/', 1)
    api = 'https://api.github.com/repos/HiiragiNemu/MagiaExedraTWTools/releases/tags/' + tag
    with opener.open(urllib.request.Request(api, headers={'User-Agent': 'Exedra-JP-ReleaseCheck'}), timeout=45) as response:
        data = json.load(response)
    asset = next((a for a in data['assets'] if a['name'] == filename), None)
    if not asset:
        raise ValueError('Published release has no matching XAPK asset')
    if asset['size'] != release['length'] or asset.get('digest') != 'sha256:' + release['sha256']:
        raise ValueError('Published asset size or SHA-256 differs from manifest')
    with opener.open(urllib.request.Request(url, method='HEAD'), timeout=45) as response:
        if response.status != 200 or int(response.headers['Content-Length']) != release['length']:
            raise ValueError('Anonymous download status or length mismatch')
    return {'ok': True, 'version': release['versionName'], 'url': url,
            'anonymousHttpStatus': 200, 'length': release['length'], 'sha256': release['sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'manifests/jp-known-releases.json')
    parser.add_argument('--proxy', help='Optional explicit HTTP proxy for this check only')
    args = parser.parse_args()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': args.proxy, 'https': args.proxy} if args.proxy else {}))
    print(json.dumps(check(json.loads(args.manifest.read_text(encoding='utf-8')), opener), indent=2))


if __name__ == '__main__':
    main()
