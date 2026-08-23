/* NN-4718 - Monitoramento 1 / panel 79

   api_key is created on demand. A confirmed, active account without a row is
   expected until a product flow asks for the credential. The invariant is:
   once a lazy-creation request is recorded, the user must have api_key after
   the five-minute grace period.

   This query intentionally returns only a count and never selects credential
   values, tokens, user ids, account ids or credential metadata.
*/
WITH creation_requests AS (
  SELECT
    event.id_user,
    MAX(event.created_at) AS last_creation_request_at
  FROM desenvolvimento.audit_log_events event
    FORCE INDEX (idx_audit_log_events_action)
  WHERE event.action_type = 'api_credentials'
    AND event.action_name = 'api_key_lazy_creation_requested'
  GROUP BY event.id_user
)
SELECT
  COUNT(*) AS unresolved_api_key_creation_requests
FROM creation_requests request
JOIN desenvolvimento.user user_account
  ON user_account.id = request.id_user
JOIN astpp.accounts account
  ON account.id = user_account.id_astpp
LEFT JOIN desenvolvimento.api_key api_key_row
  ON api_key_row.id_user = user_account.id
WHERE request.last_creation_request_at <= NOW() - INTERVAL 5 MINUTE
  AND api_key_row.id IS NULL
  AND user_account.id_profile = 1
  AND user_account.confmail = 1
  AND COALESCE(user_account.blocked, 0) = 0
  AND user_account.deactivated_at IS NULL
  AND COALESCE(account.status, 1) = 0
  AND COALESCE(account.reseller_id, 0) = 0
  AND NOT EXISTS (
    SELECT 1
    FROM desenvolvimento.user protected_user
    WHERE protected_user.id_astpp = user_account.id_astpp
      AND protected_user.id_profile IN (11, 12)
  );
