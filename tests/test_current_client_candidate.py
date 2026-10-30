import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_current_candidate_versions_keep_previous_releases():
    for region, version, code, old in [('jp','3.22.0',26102219,['3.21.2','3.21.1','3.21.0','3.18.0']),('tw','1.1.4',26091812,['1.1.3','1.1.2','1.0.5'])]:
        name='jp-known-releases.json' if region=='jp' else 'known-releases.json'
        m=json.loads((ROOT/'manifests'/name).read_text('utf-8'))
        assert m['latestVersion']==version
        assert m['releases'][0]['versionCode']==code
        assert [r['versionName'] for r in m['releases'][1:]]==old
        e=json.loads((ROOT/'docs'/f'{region.upper()}_CLIENT_{version}_VERIFICATION.json').read_text('utf-8'))
        assert e['signatureVerification']['status']=='PASS'
        assert e['runtime']['installation']=='NOT_TESTED_FOR_THIS_VERSION'
        assert e['runtime']['loginAndGameplay']=='NOT_TESTED_FOR_THIS_VERSION'
        assert e['publicationStatus'] == 'PUBLISHED'
        assert e['xapk']['sha256']==m['releases'][0]['sha256']
        if region == 'jp':
            assert m['publicationStatus'] == 'PUBLISHED'
            assert m['releases'][0]['publicationStatus'] == 'PUBLISHED'
            assert 'candidateUsage' not in m
            receipt = m['publicationVerification']
            assert receipt == e['publicationVerification']
            assert receipt['status'] == 'PASS'
            assert receipt['authenticated'] is False
            asset = next(a for a in receipt['assets'] if a['name'].endswith('.xapk'))
            assert asset['url'] == m['latestEndpoint']
            assert asset['bytes'] == m['releases'][0]['length']
            assert asset['githubDigest'] == 'sha256:' + m['releases'][0]['sha256']
            assert asset['rangeMatchesLocal'] is True
            assert e['toolsVersion'] == '1.4.3'
