# nvoip-zabbix

Integração do Zabbix com a API v2 da Nvoip para alertas por SMS e torpedo de voz.

## O que mudou

Os scripts antigos usavam a API v1 com `token_auth`.

Esta versão já usa:

- OAuth da API v2
- `numbersip` + `user-token`
- endpoint `/v2/sms`
- endpoint `/v2/torpedo/voice`

## Arquivos principais

- `Scripts/send_sms_nvoip_zabbix.sh`
- `Scripts/send_torpedovoz_nvoip_zabbix.sh`
- `Scripts/nvoip_zabbix_common.sh`
- `templates/media-types.md`

## Variáveis de ambiente necessárias

Defina no host do Zabbix ou no ambiente do serviço:

```bash
export NVOIP_NUMBERSIP="seu_numbersip"
export NVOIP_USER_TOKEN="seu_user_token"
export NVOIP_OAUTH_CLIENT_ID="seu_client_id"
export NVOIP_OAUTH_CLIENT_SECRET="seu_client_secret"
export NVOIP_CALLER="1049"
```

## Instalação

1. Copie os scripts para o `AlertScriptsPath` do seu Zabbix.
2. Ajuste permissões para o usuário do serviço Zabbix.
3. Garanta que `curl` e `sed` estejam disponíveis.
4. Configure os Media Types com base em `templates/media-types.md`.

## Media Types

### SMS Nvoip

- Script: `send_sms_nvoip_zabbix.sh`
- Parâmetros:
  - `{ALERT.SENDTO}`
  - `{ALERT.SUBJECT}`
  - `{ALERT.MESSAGE}`
  - `{HOST.NAME1}`

### Torpedo de Voz Nvoip

- Script: `send_torpedovoz_nvoip_zabbix.sh`
- Parâmetros:
  - `{ALERT.SENDTO}`
  - `{ALERT.SUBJECT}`

## Observações

- o token OAuth é gerado em cada execução do script
- isso simplifica a configuração e evita depender de token manual expirada
- para uso muito intenso, vale considerar cache local de token com controle de expiração

## Documentação oficial

- https://nvoip.docs.apiary.io/
- https://www.nvoip.com.br/api
