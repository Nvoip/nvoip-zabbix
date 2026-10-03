from pathlib import Path
cases=[(10,1999,20),(11,1000,10),(12,2001,20),(13,3000,21),(14,2,2),(15,5,0)]
s=['CREATE DATABASE desenvolvimento; USE desenvolvimento; CREATE TABLE mail_sender (id BIGINT AUTO_INCREMENT PRIMARY KEY,id_template INT,sent SMALLINT,status_bounce VARCHAR(20),date_created TIMESTAMP,KEY idx_date_created(date_created));']
rows=[]
for template,total,technical in cases:
 for i in range(total):
  status=['invalid:email','lim:account','processing_failed'][i%3] if i<technical else ('bounce:p' if template==15 else '')
  sent=-1 if i<technical or template==15 else 1
  rows.append(f"({template},{sent},'{status}',NOW()-INTERVAL 1 HOUR)")
rows += ["(NULL,-1,'invalid:email',NOW())", "(99,-1,'processing_failed',NOW()-INTERVAL 25 HOUR)"]
for i in range(0,len(rows),500): s.append('INSERT INTO mail_sender(id_template,sent,status_bounce,date_created) VALUES '+','.join(rows[i:i+500])+';')
Path('seed.sql').write_text('\n'.join(s))
