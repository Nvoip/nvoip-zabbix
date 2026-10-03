"""Run against the isolated synthetic fixture, with SMTP disabled."""
import base64,json,urllib.request
request=urllib.request.Request('http://127.0.0.1:13358/api/prometheus/grafana/api/v1/rules',headers={'Authorization':'Basic '+base64.b64encode(b'admin:nn5258-fixture').decode()})
with urllib.request.urlopen(request) as response:
    groups=json.load(response)['data']['groups']
rules={r['uid']:r for g in groups for r in g['rules']}
expected={'nn5258-threshold':{'10','13','14'},'nn5258-total':{'14'}}
for uid,firing in expected.items():
    rule=rules[uid]
    assert rule['health']=='ok' and not rule.get('lastError'),rule
    assert {a['labels']['template_id'] for a in rule['alerts'] if a['state']=='Alerting'}==firing
    assert {a['labels']['template_id'] for a in rule['alerts']}=={'10','11','12','13','14','15'}
print('Grafana 11.6.14 actual rule evaluation PASS: boundary/count/total/bounce exclusions')
