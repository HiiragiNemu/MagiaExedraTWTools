import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_current_candidate_versions_keep_previous_releases():
    for region, version, code, old in [('jp','3.21.1',26101610,['3.21.0','3.18.0']),('tw','1.1.4',26091812,['1.1.3','1.1.2','1.0.5'])]:
        name='jp-known-releases.json' if region=='jp' else 'known-releases.json'
        m=json.loads((ROOT/'manifests'/name).read_text('utf-8'))
        assert m['latestVersion']==version
        assert m['releases'][0]['versionCode']==code
        assert [r['versionName'] for r in m['releases'][1:]]==old
        e=json.loads((ROOT/'docs'/f'{region.upper()}_CLIENT_{version}_VERIFICATION.json').read_text('utf-8'))
        assert e['signatureVerification']['status']=='PASS'
        assert e['runtime']['installation']=='NOT_TESTED_FOR_THIS_VERSION'
        assert e['runtime']['loginAndGameplay']=='NOT_TESTED_FOR_THIS_VERSION'
        assert e['publicationStatus'] in {'PENDING_PUBLICATION','PUBLISHED'}
        assert e['xapk']['sha256']==m['releases'][0]['sha256']
