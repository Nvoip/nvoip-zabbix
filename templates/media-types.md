# Zabbix media types

Para instalações Zabbix 7.0 ou superiores, prefira o Webhook importável
`media_nvoip.yaml`. Ele cobre SMS, WhatsApp por template aprovado e torpedo de
voz com OAuth, dry-run seguro e retries do próprio Zabbix. O passo a passo está
em `../docs/zabbix-nvoip-alerts.md`.

Os Media Types de script abaixo permanecem disponíveis para instalações que
ainda não usam o Webhook. Os scripts atualizados também usam API V3 e OAuth
por padrão, com Python 3 como dependência. Siga
[`../docs/script-migration.md`](../docs/script-migration.md) antes de atualizar
um servidor existente. O endpoint histórico `/integrations/nvoip/sms` não
deve continuar configurado.

Este arquivo descreve os parâmetros para criar os Media Types em
`Administration > Media types > Create media type`.

As credenciais da Nvoip devem ficar como variáveis de ambiente no host do
Zabbix, não como parâmetros do Media Type.

## SMS Nvoip

- Type: `Script`
- Script name: `send_sms_nvoip_zabbix.sh`
- Parameters:
  - `{ALERT.SENDTO}`
  - `{ALERT.SUBJECT}`
  - `{ALERT.MESSAGE}`
  - `{HOST.NAME1}`

## Torpedo de Voz Nvoip

- Type: `Script`
- Script name: `send_torpedovoz_nvoip_zabbix.sh`
- Parameters:
  - `{ALERT.SENDTO}`
  - `{ALERT.SUBJECT}`
  - `{ALERT.MESSAGE}`
