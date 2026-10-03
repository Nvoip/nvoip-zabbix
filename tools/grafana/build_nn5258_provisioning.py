"""NN-5258: deterministic provisioning of a scoped dashboard and two alert rules."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / 'docs/grafana'
OUT = SQL / 'nn5258-provisioning'
UID = 'nn5258-mail-rejections'
DATASOURCE = {'type': 'mysql', 'uid': '000000007'}
MUTE = 'NN-5258-pending-contact'


def target(filename, fmt='table'):
    return {'refId': 'A', 'datasource': DATASOURCE, 'rawSql': (SQL / filename).read_text(),
            'format': fmt, 'rawQuery': True, 'editorMode': 'code'}


def build():
    OUT.mkdir(exist_ok=True)
    series = target('mail-sender-technical-rejection-series.sql', 'time_series')
    metrics = target('mail-sender-technical-rejection-alerts.sql')
    dashboard = {'uid': UID, 'title': 'E-mails — rejeições técnicas por template',
                 'tags': ['NN-5258', 'e-mails'], 'schemaVersion': 40, 'version': 1,
                 'editable': True, 'timezone': 'browser', 'refresh': '5m',
                 'time': {'from': 'now-24h', 'to': 'now'}, 'panels': [
        {'id': 1, 'title': 'Últimas 24 h por template e status (hora)', 'type': 'timeseries',
         'datasource': DATASOURCE, 'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 10},
         'targets': [series], 'fieldConfig': {'defaults': {'custom': {'drawStyle': 'bars',
          'fillOpacity': 30}, 'unit': 'short'}, 'overrides': []},
         'options': {'legend': {'displayMode': 'table', 'placement': 'bottom'},
                     'tooltip': {'mode': 'multi'}}},
        {'id': 2, 'title': 'Volume e rejeição técnica por template — 24 h', 'type': 'table',
         'datasource': DATASOURCE, 'gridPos': {'x': 0, 'y': 10, 'w': 24, 'h': 9},
         'targets': [metrics], 'fieldConfig': {'defaults': {}, 'overrides': [
           {'matcher': {'id': 'byName', 'options': 'technical_rejection_pct_24h'},
            'properties': [{'id': 'decimals', 'value': 4}, {'id': 'unit', 'value': 'percent'}]}]},
         'options': {'showHeader': True}},
        {'id': 3, 'title': 'Estado das duas regras de rejeição técnica', 'type': 'alertlist',
         'gridPos': {'x': 0, 'y': 19, 'w': 24, 'h': 7},
         'options': {'dashboardAlerts': False, 'alertName': 'NN-5258',
                     'alertInstanceLabelFilter': '{jira="NN-5258"}',
                     'showInstances': True, 'groupMode': 'default', 'viewMode': 'list',
                     'sortOrder': 1, 'maxItems': 20,
                     'stateFilter': {'firing': True, 'pending': True, 'noData': True,
                                     'normal': True, 'error': True}}},
        {'id': 4, 'title': 'Critérios e entrega de notificação', 'type': 'text',
         'gridPos': {'x': 0, 'y': 26, 'w': 24, 'h': 5},
         'options': {'mode': 'markdown', 'content':
          'Rejeição técnica: `sent=-1` com `invalid:*`, `lim:*` ou `processing_failed`. '
          'Regra 1: >1% **ou** >20 em 24 h, sem arredondar o limiar. '
          'Regra 2: 100% do template. Bounce real fica fora do numerador.\n\n'
          '**As regras são avaliadas; notificações estão silenciadas até configurar '
          'um destinatário operacional válido.** O receiver existente é um endereço de exemplo. '
          '[Servidor E-mails](/grafana/d/saJohhCIk)'}}]}
    rules = []
    for suffix, title, filename in [
        ('threshold', 'NN-5258 — rejeição técnica >1% ou >20 em 24 h',
         'mail-sender-technical-rejection-threshold.sql'),
        ('total', 'NN-5258 — template com 100% de rejeição técnica em 24 h',
         'mail-sender-technical-rejection-total.sql')]:
        query = target(filename)
        rules.append({'uid': 'nn5258-' + suffix, 'title': title, 'condition': 'B',
                      'data': [
            {'refId': 'A', 'datasourceUid': DATASOURCE['uid'],
             'relativeTimeRange': {'from': 86400, 'to': 0}, 'model': query},
            {'refId': 'B', 'datasourceUid': '__expr__',
             'relativeTimeRange': {'from': 0, 'to': 0},
             'model': {'refId': 'B', 'type': 'math', 'expression': '$A > 0',
                       'datasource': {'type': '__expr__', 'uid': '__expr__'},
                       'intervalMs': 1000, 'maxDataPoints': 43200}}],
            'dashboardUid': UID, 'panelId': 2, 'noDataState': 'OK', 'execErrState': 'Error',
            'for': '0s', 'isPaused': False, 'labels': {'jira': 'NN-5258', 'service': 'mail-sender'},
            'annotations': {'__dashboardUid__': UID, '__panelId__': '2',
                            'summary': 'Template {{ $labels.template_id }}: rejeição técnica nas últimas 24 h'},
            'notification_settings': {'receiver': 'grafana-default-email',
                                       'mute_time_intervals': [MUTE]}})
    alerting = {'apiVersion': 1,
                'muteTimes': [{'orgId': 1, 'name': MUTE, 'time_intervals': [
                    {'times': [{'start_time': '00:00', 'end_time': '24:00'}]}]}],
                'groups': [{'orgId': 1, 'name': 'NN-5258-mail-sender',
                            'folder': 'Nvoip', 'interval': '300s', 'rules': rules}]}
    for filename, data in [('dashboard.json', dashboard), ('alerting.json', alerting)]:
        (OUT / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    provider = {'apiVersion': 1, 'providers': [{'name': 'nn5258-mail-sender', 'orgId': 1,
        'folder': 'Nvoip', 'type': 'file', 'disableDeletion': False,
        'updateIntervalSeconds': 30, 'allowUiUpdates': True,
        'options': {'path': '/var/lib/grafana/dashboards-nn5258',
                    'foldersFromFilesStructure': False}}]}
    (OUT / 'provider.yaml').write_text(json.dumps(provider, indent=2) + '\n')


if __name__ == '__main__':
    build()
