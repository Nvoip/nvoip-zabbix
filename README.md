# nvoip-zabbix

[![Nvoip](https://img.shields.io/badge/Nvoip-site-00A3E0?style=flat-square)](https://www.nvoip.com.br/) [![API v2](https://img.shields.io/badge/API-v2-1F6FEB?style=flat-square)](https://www.nvoip.com.br/api/) [![Docs](https://img.shields.io/badge/docs-Apiary-6A737D?style=flat-square)](https://nvoip.docs.apiary.io/) [![Postman](https://img.shields.io/badge/Postman-workspace-FF6C37?style=flat-square)](https://nvoip-api.postman.co/workspace/e671d01f-168a-4c38-8d0e-c217229dd61a/team-quickstart) [![Stack](https://img.shields.io/badge/stack-Zabbix-D40000?style=flat-square)](https://github.com/Nvoip/nvoip-api-examples) [![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square)](LICENSE)

Integração oficial da [Nvoip](https://www.nvoip.com.br/) para alertas do Zabbix via API v2 com SMS e torpedo de voz.

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

## Links oficiais

- [Site da Nvoip](https://www.nvoip.com.br/)
- [Documentação da API](https://nvoip.docs.apiary.io/)
- [Página da API](https://www.nvoip.com.br/api/)
- [Workspace Postman](https://nvoip-api.postman.co/workspace/e671d01f-168a-4c38-8d0e-c217229dd61a/team-quickstart)
- [Hub de exemplos](https://github.com/Nvoip/nvoip-api-examples)
