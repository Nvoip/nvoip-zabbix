# Zabbix integration proposal metadata

This file contains the public, non-contact information prepared for the Zabbix
**Propose integration** vendor form. Submission of the form is a separate
external publication step.

| Field | Proposed value |
| --- | --- |
| Integration title | Nvoip notifications for Zabbix |
| Company name | Nvoip |
| Company description | Nvoip provides cloud communication APIs for voice, SMS, and WhatsApp. |
| Source | https://github.com/Nvoip/nvoip-zabbix |
| Created | 2026-08-28 |
| Updated | 2026-08-28 |
| Author | Nvoip |
| Logo | `assets/nvoip-logo.svg` |
| Compatibility | Nvoip API v3 accounts with SMS, voice, and/or approved WhatsApp template capabilities |
| Zabbix versions | Zabbix 7.0 and 7.4; import tested on 7.0.30 and 7.4.14 |

## Integration description

Nvoip notifications for Zabbix is an importable webhook media type that routes
trigger notifications through the Nvoip API v3. A Zabbix user can receive an
SMS, an approved WhatsApp template message, or a dynamic voice message by
selecting the channel in the media destination. Default messages include the
problem, host, severity, tags, event ID, date/time, and event URL.

The media type supports OAuth client credentials, provider-side eligibility
and rate-limit enforcement, safe error classification, and Zabbix-controlled
retries. It is distributed disabled and in dry-run mode, and voice recovery
notifications are disabled by default.

## Submission prerequisites not stored here

The vendor form also requires a business contact name, job title, business
email address, phone number, country or territory, privacy consent, and a
captcha. These values must be provided and submitted by an authorized Nvoip
representative; they are intentionally not committed to this repository.
