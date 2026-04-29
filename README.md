# nvoip-zabbix

Integracao do Zabbix com a API v2 da Nvoip para alertas por SMS e torpedo de voz.

## O que mudou

Os scripts antigos usavam a API v1 com `token_auth`.

Esta versao ja usa:

- OAuth da API v2
- `numbersip` + `user-token`
- endpoint `/v2/sms`
- endpoint `/v2/torpedo/voice`

## Arquivos principais

- `Scripts/send_sms_nvoip_zabbix.sh`
- `Scripts/send_torpedovoz_nvoip_zabbix.sh`
- `Scripts/nvoip_zabbix_common.sh`
- `templates/media-types.md`

## Variaveis de ambiente necessarias

Defina no host do Zabbix ou no ambiente do servico:

```bash
export NVOIP_NUMBERSIP="seu_numbersip"
export NVOIP_USER_TOKEN="seu_user_token"
export NVOIP_CALLER="1049"
```

## Instalacao

1. Copie os scripts para o `AlertScriptsPath` do seu Zabbix.
2. Ajuste permissoes para o usuario do servico Zabbix.
3. Garanta que `curl` e `sed` estejam disponiveis.
4. Configure os Media Types com base em `templates/media-types.md`.

## Media Types

### SMS Nvoip

- Script: `send_sms_nvoip_zabbix.sh`
- Parametros:
  - `{ALERT.SENDTO}`
  - `{ALERT.SUBJECT}`
  - `{ALERT.MESSAGE}`
  - `{HOST.NAME1}`

### Torpedo de Voz Nvoip

- Script: `send_torpedovoz_nvoip_zabbix.sh`
- Parametros:
  - `{ALERT.SENDTO}`
  - `{ALERT.SUBJECT}`

## Observacoes

- o token OAuth e gerado em cada execucao do script
- isso simplifica a configuracao e evita depender de token manual expirado
- para uso muito intenso, vale considerar cache local de token com controle de expiracao

## Documentacao oficial

- https://nvoip.docs.apiary.io/
- https://www.nvoip.com.br/api
