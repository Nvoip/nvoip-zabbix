/* NN-5258 - Série por template e status de envio nos últimos 24 h.

   Não projeta destinatário, conta, assunto, corpo nem identificador de usuário.
   O filtro por date_created usa o índice existente idx_date_created.
*/
WITH recent_messages AS (
  SELECT
    id_template,
    sent,
    COALESCE(NULLIF(status_bounce, ''), 'sem_status') AS status_bounce,
    CASE
      WHEN sent = -1
       AND (
         status_bounce LIKE 'invalid:%'
         OR status_bounce LIKE 'lim:%'
         OR status_bounce = 'processing_failed'
       ) THEN 1
      ELSE 0
    END AS technical_rejection
  FROM desenvolvimento.mail_sender FORCE INDEX (idx_date_created)
  WHERE date_created >= NOW() - INTERVAL 1 DAY
    AND id_template IS NOT NULL
)
SELECT
  id_template AS template_id,
  status_bounce,
  COUNT(*) AS messages_with_status_24h,
  SUM(technical_rejection) AS technical_rejections_24h
FROM recent_messages
GROUP BY id_template, status_bounce
ORDER BY id_template, status_bounce;
