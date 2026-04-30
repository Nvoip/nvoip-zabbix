# Zabbix media types

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
