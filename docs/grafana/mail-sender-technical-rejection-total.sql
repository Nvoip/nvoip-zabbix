/* NN-5258 - Uma medida numérica por template para alerta multidimensional. */
WITH recent_messages AS (
  SELECT id_template,
    CASE WHEN sent = -1 AND (status_bounce LIKE 'invalid:%'
      OR status_bounce LIKE 'lim:%' OR status_bounce = 'processing_failed')
      THEN 1 ELSE 0 END AS technical_rejection
  FROM desenvolvimento.mail_sender FORCE INDEX (idx_date_created)
  WHERE date_created >= NOW() - INTERVAL 1 DAY AND id_template IS NOT NULL
)
SELECT CAST(id_template AS CHAR) AS template_id,
  CAST((SUM(technical_rejection) > 0 AND SUM(technical_rejection) = COUNT(*)) AS DECIMAL(10,0)) AS alert_value
FROM recent_messages
GROUP BY id_template
ORDER BY id_template;
