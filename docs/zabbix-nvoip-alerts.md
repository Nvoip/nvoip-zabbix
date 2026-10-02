# Alertas Zabbix por SMS, WhatsApp e chamada

O arquivo `templates/media_nvoip.yaml` contém um media type Webhook para
Zabbix 7.0 ou superior. Ele usa os endpoints atuais da API v3 da Nvoip:

- `POST /v3/sms/sendTemplate`;
- `POST /v3/wa/templateMessages`, sempre com template aprovado;
- `POST /v3/torpedo/voice`.

As requisições OAuth e de notificação se identificam com o cabeçalho
`User-Agent: Nvoip-Zabbix/1.0 (+https://github.com/Nvoip/nvoip-zabbix)`.
Isso evita a rejeição Cloudflare 1010 observada em requisições sem identificação
adequada, preservando as regras de segurança da API.

O media type sai desabilitado e com `nvoip_dry_run=1`. Importar o arquivo não
envia mensagens nem ligações.

## 1. Importar

1. Em **Alerts > Media types**, selecione **Import**.
2. Importe `templates/media_nvoip.yaml` com **Create new** marcado.
3. Mantenha **Nvoip alerts** desabilitado durante a configuração.

O export é compatível com o formato do Zabbix 7.0 LTS e teve a importação
validada nas versões 7.0.30 e 7.4.14. O JavaScript usa somente `HttpRequest`,
`btoa` e recursos documentados pelo Zabbix.

## 2. Cadastrar credenciais como macros secretas

Crie as macros abaixo como **Secret text** ou **Vault secret**. Não substitua
os placeholders diretamente no YAML e não grave valores reais no Git:

| Macro | Uso |
| --- | --- |
| `{$NVOIP.OAUTH.CLIENT_ID}` | client ID OAuth fornecido pela Nvoip |
| `{$NVOIP.OAUTH.CLIENT_CREDENTIAL}` | credencial do cliente OAuth fornecida pela Nvoip |

O modo padrão `nvoip_auth_mode=client_credentials` troca essas credenciais por
um bearer de curta duração em cada execução. Esse é o grant indicado pela API
v3 para integrações servidor a servidor. O parâmetro `nvoip_oauth_scopes` sai
com `sms:send call:make` e deve ser limitado aos grants do cliente cadastrado.
Como alternativa operacional, o modo
`bearer` usa `{$NVOIP_ACCESS_TOKEN}`; ele só é indicado quando a renovação do
token já é controlada externamente.

Não exponha macros secretas em mensagem, assunto, `Send to`, logs ou captura de
tela. O webhook registra somente canal, ID do evento e status HTTP.

## 3. Configurar cada canal

No usuário de alertas do Zabbix, adicione o media type uma vez para cada canal.
O campo **Send to** define canal e destino:

```text
sms:5511999999999
whatsapp:5511999999999
voice:5511999999999
```

SMS aceita 11 a 16 dígitos, WhatsApp aceita 8 a 20 e chamada aceita 8 a 13.
O sinal `+` inicial é opcional e não é enviado à API.

### SMS com modelos aprovados

No Painel Nvoip, abra **Templates > SMS**, selecione os modelos aprovados
`zabbix_problema`, `zabbix_recuperado` e `zabbix_atualizado` e salve uma cópia
para a sua conta. Configure os IDs dessas cópias nas macros abaixo; não use
IDs do catálogo global nem de outra conta.

| Macro | Modelo |
| --- | --- |
| `{$NVOIP.SMS.PROBLEM_TEMPLATE_ID}` | `zabbix_problema` |
| `{$NVOIP.SMS.RECOVERY_TEMPLATE_ID}` | `zabbix_recuperado` |
| `{$NVOIP.SMS.UPDATE_TEMPLATE_ID}` | `zabbix_atualizado` |

Os textos e o contrato estão em [`sms_models.json`](../templates/sms_models.json).
Cada modelo recebe cinco variáveis: nome do evento (40 caracteres), host (20),
severidade (12), ID do evento (20) e data/hora (19). O Webhook limita cada
variável e usa a data de problema, recuperação ou atualização correspondente.
Uma atualização tem prioridade sobre a recuperação na seleção do modelo.
O texto final tem até 159 caracteres. O endpoint exige template ativo e
pertencente à conta OAuth. Alterações no texto exigem nova aprovação.

Não é necessário liberar texto livre. O Webhook não usa `/sms` como fallback.
A API deve fornecer `accepted` e `smsStatus` no retorno de `/sms/sendTemplate`;
uma versão anterior que retorna somente “SMS sent successfully.” é recusada
como resultado sem confirmação. Publique a API compatível antes do Webhook.

### WhatsApp

Os alertas enviam `functions.openAttendance=false` e `functions.to_flow=false`
para não abrir atendimento nem iniciar Flow ao enviar a notificação.

Configure também, como macros secretas quando aplicável:

| Macro | Uso |
| --- | --- |
| `{$NVOIP.WHATSAPP.INSTANCE}` | instância da conta habilitada |
| `{$NVOIP.WHATSAPP.TEMPLATE_ID}` | template aprovado para a conta |

O idioma padrão é `pt_BR`. O payload usa duas variáveis de corpo: assunto e
mensagem. Se o template aprovado tiver outra quantidade ou ordem, ajuste os
parâmetros `nvoip_whatsapp_body_1` a `nvoip_whatsapp_body_6`; parâmetros vazios
não são enviados. A API rejeita template, instância, destinatário ou conta sem
permissão. Algumas contas gerenciadas por revendedores não são elegíveis para
notificações por WhatsApp; confirme a elegibilidade com a Nvoip antes de
habilitar o canal.

### Chamada/torpedo de voz

Configure `{$NVOIP.VOICE.CALLER}` com a origem permitida para a conta. Por
padrão, eventos de recuperação não geram chamada mesmo que uma operação de
recovery use esse media type. Alterar `nvoip_voice_send_recovery` para `1` é
uma decisão explícita do administrador.

## 4. Preset recomendado por severidade

Use o filtro de severidades de cada mídia do usuário:

| Canal | Severidades iniciais | Recovery |
| --- | --- | --- |
| SMS | Warning e Average | opcional |
| WhatsApp | High e Disaster | opcional |
| Chamada | Disaster; High somente para plantão crítico | bloqueado por padrão |

Escalonamentos para grupos ou números diferentes devem ser configurados como
mídias/usuários e operações separadas no Zabbix. Isso mantém destinatários e
horários auditáveis sem codificá-los no webhook.

## 5. Testar sem comunicação real

Com `nvoip_dry_run=1`, use **Test** no media type e informe, por exemplo:

```text
send_to=sms:5511999999999
event_source=0
event_value=1
event_update_status=0
event_id=TEST-5769
event_name=Teste de alerta
host_name=host-teste
event_severity=Warning
event_date=2026.10.01
event_time=12:00:00
nvoip_sms_problem_template_id=<ID da cópia aprovada>
```

O resultado deve ser `status=dry_run`; nenhuma autenticação ou chamada HTTP é
feita. Repita com `whatsapp:` e `voice:`. Para recovery, use `event_value=0` e
confirme `status=skipped`, `reason=recovery_disabled` no canal de voz.

O teste funcional com `nvoip_dry_run=0` envia comunicação real e pode gerar
cobrança. Faça-o somente com conta direta, destinatários sintéticos/autorizados
e autorização operacional explícita. Esta entrega não executa esse disparo.

## 6. Ativar e acompanhar

1. Confirme que os testes em dry-run passaram e que nenhuma macro ficou com o
   placeholder literal `{$NVOIP...}`.
2. Ajuste `nvoip_dry_run=0`.
3. Mantenha `attempts=3` e `attempt_interval=10s`, ou adeque-os à política do
   ambiente.
4. Habilite o media type e associe-o apenas às actions desejadas.

Respostas `408`, `425`, `429` e `5xx` são classificadas como
`NVOIP_RETRYABLE`. Outros `4xx` são `NVOIP_PERMANENT`. O Zabbix controla as
tentativas; o texto de erro inclui fase, canal e HTTP status, nunca token ou
corpo da resposta. O ID do evento segue na mensagem padrão para correlação com
os logs da Nvoip.

No SMS, HTTP 200 só é aceito com `accepted=true` e
`smsStatus=200 - SMS Enviado com Sucesso` no JSON. HTML, JSON inválido e respostas de rejeição funcional falham, inclusive
quando HTTP é 200. `status=sent` no resultado do Webhook significa aceitação
pela API; `delivery_confirmed=false` distingue isso de recebimento no celular.
Não cadastrar o `token_auth` de scripts antigos como bearer OAuth. Consulte o
[guia de migração para o Webhook nativo](native-migration.md) para preservar instalações
existentes.

## 7. Desinstalar ou reverter

1. Desabilite as actions que usam **Nvoip alerts**.
2. Desabilite e remova o media type.
3. Remova as macros secretas somente depois de confirmar que não são usadas por
   outro media type.

Não há migration, SQL, mudança de Security Group nem alteração de permissão de
arquivo associada a este media type.

## Referências

- [Webhook media type](https://www.zabbix.com/documentation/current/en/manual/config/notifications/media/webhook)
- [Exportação e importação de media types](https://www.zabbix.com/documentation/current/en/manual/xml_export_import/media)
- [Objetos JavaScript adicionais do Zabbix](https://www.zabbix.com/documentation/current/en/manual/config/items/preprocessing/javascript/javascript_objects)
