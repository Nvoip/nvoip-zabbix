/* NN-5258 - Valores por template para as duas regras de alerta Grafana.

   technical_rejection_pct_24h alimenta a regra >1% OU >20 rejeições.
   technical_rejection_pct_24h = 100 alimenta a regra separada de rejeição
   técnica integral. A consulta não retorna dados de destinatários ou contas.
*/
WITH recent_messages AS (
  SELECT
    id_template,
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
  SUM(technical_rejection) AS technical_rejections_24h,
  COUNT(*) AS messages_24h,
  ROUND(100 * SUM(technical_rejection) / COUNT(*), 2) AS technical_rejection_pct_24h
FROM recent_messages
GROUP BY id_template
HAVING COUNT(*) > 0
ORDER BY id_template;
