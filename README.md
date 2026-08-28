# Nvoip for Zabbix

![Nvoip](assets/nvoip-logo.svg)

[![CI](https://github.com/Nvoip/nvoip-zabbix/actions/workflows/ci.yml/badge.svg)](https://github.com/Nvoip/nvoip-zabbix/actions/workflows/ci.yml)
[![Nvoip API v3](https://img.shields.io/badge/Nvoip%20API-v3-1F6FEB?style=flat-square)](https://www.nvoip.com.br/api/)
[![Zabbix 7.0+](https://img.shields.io/badge/Zabbix-7.0%2B-D40000?style=flat-square)](https://www.zabbix.com/)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square)](LICENSE)

Nvoip for Zabbix is a public webhook media type that sends Zabbix trigger
notifications through the Nvoip API v3 by SMS, approved WhatsApp template, or
voice message.

The integration is distributed as an importable YAML file. It is disabled and
uses dry-run by default, so importing it does not send a message or place a
call.

## Supported features

- SMS notifications;
- WhatsApp notifications using a template approved for the Nvoip account;
- dynamic voice messages for on-call escalation;
- problem, recovery, and update message templates;
- host, problem, severity, tags, event ID, date/time, and event URL context;
- OAuth `client_credentials` or an externally managed bearer token;
- retryable and permanent error classification without logging credentials or
  provider response bodies;
- voice recovery notifications disabled by default.

## Requirements

- Zabbix 7.0 or 7.4 (import tested on 7.0.30 and 7.4.14);
- an active Nvoip API v3 account;
- the required channel enabled for the account;
- an approved WhatsApp template and instance when using WhatsApp;
- an allowed caller number when using voice messages.

## Quick start

1. Download [`templates/media_nvoip.yaml`](templates/media_nvoip.yaml).
2. In Zabbix, go to **Alerts > Media types > Import** and create the
   **Nvoip alerts** media type.
3. Keep it disabled and keep `nvoip_dry_run=1` while configuring it.
4. Store OAuth credentials and channel identifiers in Zabbix secret or vault
   macros. Never replace the placeholders in the YAML file.
5. Add the media type to a Zabbix user with one of these **Send to** values:

   ```text
   sms:5511999999999
   whatsapp:5511999999999
   voice:5511999999999
   ```

6. Test all three routes in dry-run before enabling the integration.

Full instructions:

- [English setup, testing, and removal guide](docs/zabbix-nvoip-alerts.en.md)
- [Guia em português](docs/zabbix-nvoip-alerts.md)

## Security and privacy

- No credential or destination is embedded in the repository.
- The webhook logs only the channel, Zabbix event ID, and HTTP status.
- Account, channel, template, recipient, and rate-limit checks remain enforced
  by the Nvoip API.
- Live tests can send billable communications. Use only an authorized direct
  account and authorized test recipients.

## Marketplace metadata

The public information prepared for the Zabbix integration proposal is in
[`docs/zabbix-marketplace-listing.md`](docs/zabbix-marketplace-listing.md).
Submission through the Zabbix vendor form is a separate external publication
step.

## Legacy and Nvoip operational content

The scripts in [`Scripts/`](Scripts/) and their
[media type notes](templates/media-types.md) use the legacy API v2 integration
path and remain available for existing installations. New installations should
use the API v3 webhook above.

This repository also contains Nvoip-specific operational monitoring templates,
including:

- [Aurora lock guard](docs/database-lock-monitoring.md);
- [API key lazy-creation monitor](docs/grafana/api-key-lazy-creation-monitor.md).

These operational templates are independent from the public Nvoip notification
media type.

## Support and feedback

- [Nvoip website](https://www.nvoip.com.br/)
- [Nvoip API page](https://www.nvoip.com.br/api/)
- [Nvoip API Postman workspace](https://nvoip-api.postman.co/workspace/e671d01f-168a-4c38-8d0e-c217229dd61a/team-quickstart)
- [Repository issues](https://github.com/Nvoip/nvoip-zabbix/issues)
