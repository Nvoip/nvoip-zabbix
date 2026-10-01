# Migrar scripts de alertas para a API V3

Para Zabbix 7.0+, prefira o [Webhook nativo](zabbix-nvoip-alerts.md). Esta opção
por scripts mantém os nomes públicos e os argumentos dos Media Types antigos
para instalações que precisam desse formato. Atualizar o repositório não
atualiza automaticamente os arquivos ou a configuração de servidores Zabbix.

## Configuração atual

- SMS: `POST https://api.nvoip.com.br/v3/sms`.
- Torpedo de voz: `POST https://api.nvoip.com.br/v3/torpedo/voice`.
- OAuth: `POST https://api.nvoip.com.br/auth/oauth2/token`, grant
  `client_credentials`, seguido de bearer na API.
- Dependência: Python 3. Nenhum pacote Python adicional é necessário.

O token `token_auth` do endpoint histórico `/integrations/nvoip/sms` não é um
bearer OAuth e não deve ser copiado para `NVOIP_ACCESS_TOKEN`. Cadastrar um
cliente OAuth da conta que enviará os alertas é pré-condição da migração.

Configure as variáveis da [.env.example](../.env.example) no ambiente do
serviço Zabbix, usando o mecanismo de segredos do servidor. O programa não
carrega `.env` automaticamente. Não coloque credenciais em argumentos do
Media Type, no Git ou no conteúdo das mensagens.

`NVOIP_OAUTH_SCOPES` pode restringir os scopes aos grants do cliente. Na sua
ausência, o script solicita `sms:send` para SMS e `call:make` para voz. O modo
`NVOIP_AUTH_MODE=bearer` exige `NVOIP_ACCESS_TOKEN` válido e renovação externa.

## Atualizar uma instalação

1. Identifique scripts, mídias, ações e destinatários atuais. Faça backup dos
   arquivos e da configuração das ações. Preserve permissões preexistentes.
2. Copie os arquivos do diretório `Scripts/` juntos, incluindo
   `nvoip_zabbix_transport.py` e `nvoip_zabbix_common.sh`. Não atualize somente
   o script de SMS: os entry points dependem do transporte compartilhado.
3. Se o script antigo usa um nome diferente, como `send_sms_nvoip.sh`, crie
   uma mídia de teste apontando para `send_sms_nvoip_zabbix.sh`; não substitua
   um script compartilhado sem identificar todas as ações que o utilizam.
4. Configure o cliente OAuth da conta correta e execute
   `sh Scripts/check_nvoip_zabbix_config.sh` no mesmo ambiente do serviço.
   Esse teste autentica, mas não envia SMS nem faz ligação.
5. Teste uma ação limitada ao destinatário autorizado. Antes de habilitar
   outros alertas, confirme a aceitação pela API e o recebimento no celular.
6. Migre as demais ações explicitamente, preservando filtros, horários,
   severidades e destinatários. O código não modifica esses dados.

Para rollback, restaure os arquivos e a associação anterior das ações. Não
revogue credenciais compartilhadas nem remova macros usadas por outras mídias.

## Falhas e limite de tamanho

O SMS usa JSON serializado, até 160 unidades UTF-16, sem cortar um par
surrogate. Aspas, barras, quebras de linha e acentos não invalidam o JSON.
`NVOIP_SMS_MAX_CHARS` só aceita valores de 1 a 160.

HTTP não 2xx, HTML de challenge ou resposta JSON inválida terminam com código
de saída diferente de zero. O SMS só termina com sucesso quando a resposta
traz `status=200 - SMS Enviado com Sucesso`, conforme o contrato V2/V3;
rejeições funcionais dentro de HTTP 200 também falham. Logs não contêm bearer,
credencial, número, texto do SMS ou corpo recebido.

O resultado `status=accepted`, `delivery_confirmed=false` indica aceitação
pela API. Confirmação de entrega exige evidência do provedor/destinatário.
O programa não repete requisições automaticamente; configure as tentativas no
Zabbix e considere duplicatas quando o transporte terminar com entrega
desconhecida. O timeout HTTP padrão é 10 segundos por requisição, configurável
de 1 a 15, para acomodar autenticação e envio no timeout da mídia.

## Compatibilidade V2 explícita

Instalações ainda dependentes do password grant podem manter temporariamente
`NVOIP_BASE_URL=https://api.nvoip.com.br/v2` e
`NVOIP_AUTH_MODE` no modo `password`, com `NVOIP_NUMBERSIP`, `NVOIP_USER_TOKEN`,
`NVOIP_OAUTH_CLIENT_ID` e `NVOIP_OAUTH_CLIENT_SECRET`. Nesse modo, OAuth usa
`/v2/oauth/token` e SMS usa `/v2/sms`. Não há fallback automático da V3 para V2
nem para `/integrations/`; alterar apenas a URL sem adequar o grant é recusado.

## English migration notes

For Zabbix 7.0+, prefer the [native webhook](zabbix-nvoip-alerts.en.md).
The maintained script entry points now default to API v3 and OAuth
`client_credentials`. Install all files in `Scripts/` together and provide
Python 3. Configure the environment using `.env.example`; files named `.env`
are not automatically loaded. Keep credentials out of media arguments and Git.

The historical `token_auth` credential is not an OAuth bearer. Provision the
OAuth client for the correct sending account before switching actions. Run
`check_nvoip_zabbix_config.sh` under the Zabbix service environment to check
authentication without sending notifications. Test only an authorized
recipient, verify API acceptance and handset receipt, then migrate other
actions explicitly. Preserve existing permissions, destinations, filters and
rollback associations.

SMS checks both HTTP status and the V2/V3 business response; HTTP 200 with an
SMS rejection is a failure. Output `accepted` means API acceptance, not handset
delivery. Credentials and response bodies are never logged, and the transport
does not retry automatically. Explicit V2/password-grant compatibility remains
available during migration; retired `/integrations/` URLs are rejected.
