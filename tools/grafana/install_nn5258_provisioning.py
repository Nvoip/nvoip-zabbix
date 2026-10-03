"""NN-5258 scoped initial provisioning; run as root with reviewed staging directory."""
import argparse
import grp
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--staging', required=True, type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('root required')
    sources = {n: args.staging / n for n in ('provider.yaml', 'dashboard.json', 'alerting.json')}
    documents = {n: json.loads(p.read_text()) for n, p in sources.items()}
    assert documents['dashboard.json']['uid'] == 'nn5258-mail-rejections'
    rules = documents['alerting.json']['groups'][0]['rules']
    assert {r['uid'] for r in rules} == {'nn5258-threshold', 'nn5258-total'}
    assert documents['alerting.json']['groups'][0]['interval'] == '300s'
    assert all(r['notification_settings']['mute_time_intervals'] == ['NN-5258-pending-contact'] for r in rules)
    assert documents['alerting.json']['muteTimes'][0]['time_intervals'] == [{'times': [{'start_time': '00:00', 'end_time': '24:00'}]}]
    targets = {'provider.yaml': Path('/etc/grafana/provisioning/dashboards/nn5258.yaml'),
               'dashboard.json': Path('/var/lib/grafana/dashboards-nn5258/dashboard.json'),
               'alerting.json': Path('/etc/grafana/provisioning/alerting/nn5258.json')}
    if any(p.exists() for p in targets.values()):
        raise SystemExit('NN-5258 target occupied; review existing version before updating')
    db = sqlite3.connect('file:/var/lib/grafana/grafana.db?mode=ro', uri=True)
    assert db.execute("SELECT COUNT(*) FROM alert_rule WHERE uid IN ('nn5258-threshold','nn5258-total')").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM dashboard WHERE uid='nn5258-mail-rejections'").fetchone()[0] == 0
    backup = Path(tempfile.mkdtemp(prefix='NN-5258-', dir='/var/tmp'))
    backup_db = sqlite3.connect(str(backup / 'grafana.db'))
    db.backup(backup_db)
    backup_db.close()
    db.close()
    protected = [Path('/etc/grafana/grafana.ini'), Path('/etc/grafana/provisioning/dashboards/nvoip-fila-deploy.yaml')]
    baseline = {str(p): {'sha256': digest(p), 'mode': p.stat().st_mode, 'uid': p.stat().st_uid, 'gid': p.stat().st_gid} for p in protected if p.exists()}
    (backup / 'protected.json').write_text(json.dumps(baseline, indent=2))
    gid = grp.getgrnam('grafana').gr_gid
    created = []
    try:
        for name, target in targets.items():
            if not target.parent.exists():
                target.parent.mkdir(mode=0o755)
            temporary = target.with_name(target.name + '.NN5258-stage')
            with open(temporary, 'xb') as stream:
                stream.write(sources[name].read_bytes())
            os.chown(temporary, 0, gid)
            os.chmod(temporary, 0o640)
            os.replace(temporary, target)
            created.append(target)
        subprocess.run(['systemctl', 'restart', 'grafana-server'], check=True)
        healthy = False
        for attempt in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:3000/api/health', timeout=2) as response:
                    healthy = json.load(response).get('database') == 'ok'
            except Exception:
                pass
            if healthy:
                break
            time.sleep(1)
        if not healthy:
            raise RuntimeError('Grafana health failed')
        for path, before in baseline.items():
            p = Path(path)
            assert digest(p) == before['sha256']
            assert (p.stat().st_mode, p.stat().st_uid, p.stat().st_gid) == (before['mode'], before['uid'], before['gid'])
    except Exception:
        for target in created:
            if target != targets['provider.yaml']:
                target.unlink(missing_ok=True)
        # Keep this provider with an empty directory for its own dashboard deletion.
        # Existing dashboards/providers and the live SQLite database are untouched.
        rollback = Path('/etc/grafana/provisioning/alerting/nn5258-rollback.json')
        rollback.write_text(json.dumps({'apiVersion': 1, 'deleteRules': [{'orgId': 1, 'uid': r['uid']} for r in rules],
                                       'deleteMuteTimes': [{'orgId': 1, 'name': 'NN-5258-pending-contact'}]}))
        subprocess.run(['systemctl', 'restart', 'grafana-server'], check=False)
        raise
    print(json.dumps({'backup': str(backup), 'health': 'ok', 'sha256': {n: digest(p) for n, p in targets.items()},
                      'protected_files': 'unchanged', 'notifications': 'muted'}))


if __name__ == '__main__':
    main()
