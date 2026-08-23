# API key lazy-creation monitor (NN-4718)

Target: Grafana dashboard `Monitoramento 1` (`Mn7pOWpSz`), panel `79`.

The API key lifecycle is on demand. Registration, email confirmation and an
ordinary panel login do not establish that the user needs a key. The monitor
therefore must not count every active user without a row in
`desenvolvimento.api_key`.

The backend services record `api_key_lazy_creation_requested` immediately
before generating a missing key. The query in
`api-key-lazy-creation-monitor.sql` reports only requests that still have no
row after five minutes. It is intentionally aggregate-only and excludes
reseller accounts and every account containing profile 11 or 12.

The event name is the cross-runtime contract. `painel-back-v5` records its
outcome as `requested`; the shared API v2/v3 legacy audit adapter maps every
non-error event to `success`. The monitor therefore does not filter
`action_outcome` and avoids losing API-originated requests.

## Creation points

There is no active database trigger for `desenvolvimento.api_key`, and neither
registration nor email confirmation creates a row. Missing keys are created
only when one of these paths asks for them:

- API v2 and API v3 credential creation/read endpoints, through
  `ApikeyService`.
- Painel: `NapikeyDao.findOrCreateNapikeyByIdUser`, used by SMS templates,
  WhatsApp templates and WhatsApp send/list flows.
- Painel legacy fallback: `ClientService.findNapikeyOrCreateIfDontExist`, used
  by API credential display, primary-user 2FA, operational approval and
  reseller client data display.

Rotation of an existing key is not an initial-creation request and does not
emit this event.

## Dependent flows

The key authenticates the public API v2/v3 capabilities, including calls, SMS,
WhatsApp, templates, balances, DIDs, URA, file upload, OTP/2FA and widgets. The
Painel also consumes it in webphone/onboarding, support chat, integrations,
SMS/WhatsApp templates and approval flows. HubSpot/Pipedrive adapters and Chat
Infra contain read-only consumers; they do not themselves create a missing
key. An ordinary login or recent `date_last_use` is therefore not proof of API
key demand.

## Deployment

This repository only versions the panel query. Applying it to Grafana is a
separate production operation:

1. Back up the current dashboard JSON/SQLite database.
2. Replace only panel 79's `rawSql` with the versioned SQL.
3. Confirm the dashboard version increments and the panel returns a single
   numeric value.
4. Roll back by restoring the prior panel JSON or the pre-change dashboard
   backup.

Do not apply the query before every key-creating runtime emits the dedicated
request event. A partial rollout would create blind spots, although it would
not create false positives.

Migration/SQL: none. The query is read-only and uses the existing
`audit_log_events`, `user`, `api_key` and `astpp.accounts` objects.

Manual step: update Grafana panel 79 after the backend/API releases are active.
