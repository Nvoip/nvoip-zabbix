from pathlib import Path
import subprocess,json

def query(name):
 sql=Path('sql/mail-sender-technical-rejection-'+name+'.sql').read_text()
 r=subprocess.run(['docker','exec','-i','nn5258-fixture-mysql','mysql','-uroot','-pnn5258-fixture','--batch'],input=sql,text=True,capture_output=True,check=True)
 rows=[x.split('\t') for x in r.stdout.strip().splitlines()]
 return [dict(zip(rows[0],x)) for x in rows[1:]]
threshold={int(x['template_id']):int(x['alert_value']) for x in query('threshold')}
assert threshold=={10:1,11:0,12:0,13:1,14:1,15:0},threshold
total={int(x['template_id']):int(x['alert_value']) for x in query('total')}
assert total=={10:0,11:0,12:0,13:0,14:1,15:0},total
metrics={int(x['template_id']):x for x in query('alerts')}
assert float(metrics[10]['technical_rejection_pct_24h'])>1
assert float(metrics[11]['technical_rejection_pct_24h'])==1
assert int(metrics[15]['technical_rejections_24h'])==0
series=query('series')
assert all(x['time'].endswith(':00:00') for x in series)
assert sum(int(x['messages_with_status_24h']) for x in series)==8007
assert all(int(x['template_id']) in threshold for x in series)
print(json.dumps({'threshold':threshold,'total':total,'metrics_rows':len(metrics),'series_rows':len(series),'actual_mysql8_boundary_fixture':'PASS'}))
