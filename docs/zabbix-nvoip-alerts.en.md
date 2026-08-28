# Zabbix alerts through Nvoip

The `templates/media_nvoip.yaml` file contains a webhook media type for Zabbix
7.0 and later compatible 7.x releases. It uses these Nvoip API v3 endpoints:

- `POST /v3/sms`;
- `POST /v3/wa/templateMessages`, with an approved template;
- `POST /v3/torpedo/voice`.

The imported media type is disabled and has `nvoip_dry_run=1`. Importing it
does not send a message or place a call.

## 1. Import the media type

1. Open **Alerts > Media types** and select **Import**.
2. Import `templates/media_nvoip.yaml` with **Create new** selected.
3. Keep **Nvoip alerts** disabled during configuration.

The JavaScript uses the Zabbix `HttpRequest` and `btoa` objects. The export is
versioned for Zabbix 7.0 and has been import-tested on Zabbix 7.0.30 and
7.4.14.

## 2. Store credentials securely

Create these Zabbix macros as **Secret text** or **Vault secret**. Do not
replace their placeholders in the YAML file or commit actual values:

| Macro | Purpose |
| --- | --- |
| `{$NVOIP.OAUTH.CLIENT_ID}` | OAuth client ID issued by Nvoip |
| `{$NVOIP.OAUTH.CLIENT_CREDENTIAL}` | OAuth client credential issued by Nvoip |

The default `nvoip_auth_mode=client_credentials` exchanges the credentials for
a short-lived bearer token on each execution. The default scopes are
`sms:send call:make` and must be limited to the grants assigned to the client.

As an operational alternative, `nvoip_auth_mode=bearer` reads an externally
managed token from `{$NVOIP_ACCESS_TOKEN}`.

Do not put secret macros in the subject, message, **Send to** field, logs, or
screenshots. The webhook logs only channel, event ID, and HTTP status.

## 3. Configure notification channels

Add the media type to a Zabbix user once per channel. The **Send to** value
selects the channel and destination:

```text
sms:5511999999999
whatsapp:5511999999999
voice:5511999999999
```

An optional leading `+` is accepted and is removed before sending the request.

### WhatsApp

Configure these account-specific macros:

| Macro | Purpose |
| --- | --- |
| `{$NVOIP.WHATSAPP.INSTANCE}` | enabled WhatsApp instance |
| `{$NVOIP.WHATSAPP.TEMPLATE_ID}` | template approved for the account |

The default language is `pt_BR`. The default payload uses the alert subject and
message as two body variables. If the approved template expects a different
order or count, configure `nvoip_whatsapp_body_1` through
`nvoip_whatsapp_body_6`. Empty variables are omitted.

The Nvoip API enforces account, template, instance, recipient, and channel
eligibility. Some reseller-managed accounts are not eligible for WhatsApp
notifications; contact Nvoip before enabling the channel.

### Voice message

Set `{$NVOIP.VOICE.CALLER}` to a caller allowed for the account. Recovery
events do not place a call by default. Setting `nvoip_voice_send_recovery=1`
must be an explicit administrator decision.

## 4. Recommended severity preset

Use each Zabbix user's media severity filter:

| Channel | Initial severities | Recovery |
| --- | --- | --- |
| SMS | Warning and Average | optional |
| WhatsApp | High and Disaster | optional |
| Voice | Disaster; High only for critical on-call escalation | disabled by default |

Configure different destinations and schedules as separate Zabbix users,
media entries, and actions. Do not hardcode recipients in the webhook.

## 5. Test without sending communications

Keep `nvoip_dry_run=1`, select **Test** on the media type, and use values such
as:

```text
send_to=sms:5511999999999
event_source=0
event_value=1
event_update_status=0
event_id=TEST-3168
```

The expected result is `status=dry_run`, with no authentication or HTTP
request. Repeat the test with `whatsapp:` and `voice:`.

For a voice recovery test, use `event_value=0`. The expected result is
`status=skipped` with `reason=recovery_disabled` and no HTTP request.

A test with `nvoip_dry_run=0` sends a real communication and may be billable.
Run it only with explicit operational authorization, an eligible direct
account, and authorized test recipients.

## 6. Enable and observe

1. Confirm that all dry-run tests passed.
2. Confirm no parameter still contains an unresolved `{$NVOIP...}` macro.
3. Set `nvoip_dry_run=0`.
4. Keep `attempts=3` and `attempt_interval=10s`, or adjust them to the
   environment's retry policy.
5. Enable the media type and associate it only with the intended actions.

HTTP `408`, `425`, `429`, and `5xx` responses are classified as
`NVOIP_RETRYABLE`; other `4xx` responses are `NVOIP_PERMANENT`. The error
contains the phase, channel, and HTTP status, but never the provider response
body or access token.

## 7. Remove or roll back

1. Disable actions that use **Nvoip alerts**.
2. Disable and remove the media type.
3. Remove secret macros only after confirming no other media type uses them.

The integration requires no database migration, SQL change, Security Group
change, or server file-permission change.

## References

- [Zabbix webhook media type](https://www.zabbix.com/documentation/current/en/manual/config/notifications/media/webhook)
- [Zabbix media type export and import](https://www.zabbix.com/documentation/current/en/manual/xml_export_import/media)
- [Zabbix JavaScript objects](https://www.zabbix.com/documentation/current/en/manual/config/items/preprocessing/javascript/javascript_objects)
