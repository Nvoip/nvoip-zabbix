# nvoip-zabbix

[![CI](https://github.com/Nvoip/nvoip-zabbix/actions/workflows/ci.yml/badge.svg)](https://github.com/Nvoip/nvoip-zabbix/actions/workflows/ci.yml) [![Nvoip](https://img.shields.io/badge/Nvoip-site-00A3E0?style=flat-square)](https://www.nvoip.com.br/) [![API v2](https://img.shields.io/badge/API-v2-1F6FEB?style=flat-square)](https://www.nvoip.com.br/api/) [![Docs](https://img.shields.io/badge/docs-Apiary-6A737D?style=flat-square)](https://nvoip.docs.apiary.io/) [![Postman](https://img.shields.io/badge/Postman-workspace-FF6C37?style=flat-square)](https://nvoip-api.postman.co/workspace/e671d01f-168a-4c38-8d0e-c217229dd61a/team-quickstart) [![Stack](https://img.shields.io/badge/stack-Zabbix-D40000?style=flat-square)](https://github.com/Nvoip/nvoip-api-examples) [![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square)](LICENSE)

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
- `Scripts/check_nvoip_zabbix_config.sh`
- `templates/media-types.md`

## Variáveis de ambiente necessárias

Defina no host do Zabbix ou no ambiente do serviço:

```bash
export NVOIP_NUMBERSIP="seu_numbersip"
export NVOIP_USER_TOKEN="seu_user_token"
export NVOIP_OAUTH_CLIENT_ID="seu_client_id"
export NVOIP_OAUTH_CLIENT_SECRET="seu_client_secret"
export NVOIP_CALLER="1049"
export NVOIP_SMS_MAX_CHARS="160"
```

Não use `Basic Auth` fixo salvo em arquivo. Os scripts montam o cabeçalho
OAuth em tempo de execução a partir de `NVOIP_OAUTH_CLIENT_ID` e
`NVOIP_OAUTH_CLIENT_SECRET`.

## Instalação

1. Copie os scripts para o `AlertScriptsPath` do seu Zabbix, normalmente `/usr/lib/zabbix/alertscripts`.
2. Ajuste permissões para o usuário do serviço Zabbix.
3. Garanta que `curl`, `sed`, `base64` e `cut` estejam disponíveis.
4. Defina as variáveis de ambiente no serviço do Zabbix ou em arquivo carregado pelo serviço.
5. Configure os Media Types com base em `templates/media-types.md`.

Exemplo de instalação:

```bash
sudo cp Scripts/*.sh /usr/lib/zabbix/alertscripts/
sudo chown zabbix:zabbix /usr/lib/zabbix/alertscripts/*.sh
sudo chmod 750 /usr/lib/zabbix/alertscripts/*.sh
```

Teste sem enviar SMS ou torpedo:

```bash
/usr/lib/zabbix/alertscripts/check_nvoip_zabbix_config.sh
```

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
  - `{ALERT.MESSAGE}`

## Teste manual

```bash
Scripts/send_sms_nvoip_zabbix.sh "11999999999" "Teste Zabbix" "Mensagem de teste" "zabbix-server"
Scripts/send_torpedovoz_nvoip_zabbix.sh "11999999999" "Teste Zabbix" "Mensagem de teste"
```

## Observações

- o token OAuth é gerado em cada execução do script
- isso simplifica a configuração e evita depender de token manual expirado
- o SMS é limitado a 160 caracteres por padrão por causa da regra do endpoint `/sms`
- para uso muito intenso, vale considerar cache local de token com controle de expiração

## Links oficiais

- [Site da Nvoip](https://www.nvoip.com.br/)
- [Documentação da API](https://nvoip.docs.apiary.io/)
- [Página da API](https://www.nvoip.com.br/api/)
- [Workspace Postman](https://nvoip-api.postman.co/workspace/e671d01f-168a-4c38-8d0e-c217229dd61a/team-quickstart)
- [Hub de exemplos](https://github.com/Nvoip/nvoip-api-examples)
