# Migrar scripts antigos para o Webhook nativo

O caminho recomendado é importar `templates/media_nvoip.yaml` em Zabbix 7.0
ou superior. Não é necessário instalar ou atualizar scripts de SMS no servidor.
O Webhook usa `POST https://api.nvoip.com.br/v3/sms/sendTemplate` com OAuth; o `token_auth`
legado não é um bearer OAuth e não deve ser reutilizado nesse parâmetro.

## Preparar

1. Exporte as actions e os media types envolvidos. Registre seus filtros,
   operações de problema/recuperação, usuários, destinos, horários e
   severidades. Guarde o backup em local restrito, fora do Git.
2. Confirme qual conta Nvoip deve enviar os alertas e obtenha um cliente OAuth
   autorizado para essa conta, limitado ao escopo `sms:send` para SMS.
3. No Painel, selecione e salve cópias dos modelos SMS aprovados
   `zabbix_problema`, `zabbix_recuperado` e `zabbix_atualizado`. Configure seus
   IDs em `{$NVOIP.SMS.PROBLEM_TEMPLATE_ID}`, `{$NVOIP.SMS.RECOVERY_TEMPLATE_ID}`
   e `{$NVOIP.SMS.UPDATE_TEMPLATE_ID}`. Mantenha texto livre bloqueado.
4. Importe o YAML com **Create new** em **Alerts > Media types**, sem substituir
   mídias existentes. **Nvoip alerts** deve ficar desabilitado, com
   `nvoip_dry_run=1`.
5. Configure as macros OAuth como **Secret text** ou **Vault secret**, conforme
   [o guia de configuração](zabbix-nvoip-alerts.md). Não grave as credenciais no
   YAML, nas mensagens, nos logs ou no campo **Send to**.
6. Para o primeiro teste, adicione a mídia nativa apenas ao usuário autorizado,
   com `Send to=sms:<número internacional>` (por exemplo, `sms:5511999999999`).
   Preserve os horários e as severidades da mídia antiga.

## Testar e migrar

1. Execute **Test** em dry-run e confirme `status=dry_run`, canal SMS e rota
   `/sms/sendTemplate`. Não há chamada à API nessa etapa.
2. Após configurar OAuth, faça um teste real somente para o destinatário
   autorizado, com `nvoip_dry_run=0`. Confirme tanto a aceitação da API quanto o
   recebimento no aparelho. `status=sent`/HTTP 200 sozinho não prova entrega.
3. Habilite a mídia nativa e altere somente as operações das actions escolhidas
   para usar **Nvoip alerts**. Inclua as operações de recuperação quando
   aplicável; preserve os filtros, usuários, destinos, horários e severidades.
4. Se alguma operação usa **All media**, verifique o risco de envio duplicado:
   um usuário com as mídias antiga e nova ativas pode receber ambas. Migre as
   referências antes de desativar a mídia antiga e evite uma janela de envio
   duplo. Não remova mídias usadas por outras actions.
5. Gere um evento controlado para a action migrada e sua recuperação; confira
   o histórico da action, os erros do Webhook e o recebimento. Migre as demais
   actions somente após esse aceite e dentro do escopo autorizado.

## Reverter

Se houver falha, restaure as operações e associações da mídia anterior a partir
do backup e desabilite a mídia nativa. Não apague arquivos, mude permissões nem
remova macros usadas por outras integrações. Restaurar o script antigo restaura
a configuração anterior; não garante envio quando aquele transporte já falhava.

Atualizar este repositório não migra automaticamente instalações de terceiros.

migration/SQL: none para importar o media type; os modelos precisam existir e
estar aprovados na conta antes de ativá-lo. A API deve fornecer `accepted` e
`smsStatus` em `/sms/sendTemplate`; publique essa versão antes do Webhook.
passo manual: importar o Webhook, configurar OAuth, testar o destinatário
permitido e migrar as associações das actions conforme a sequência acima.

## Scripts operacionais atualizados (NN-5546)

Os três pontos de entrada em `Scripts/` também usam OAuth `client_credentials`
em `/auth/oauth2/token`, sem ramal/usertoken ou token da v2. Requerem Python 3
no servidor. Configure `NVOIP_OAUTH_CLIENT_ID` e `NVOIP_OAUTH_CLIENT_SECRET`
no cofre/ambiente da instalação; use escopos `sms:send` e/ou `call:make`
conforme o canal. O script de SMS exige `NVOIP_SMS_TEMPLATE_ID` de um modelo
aprovado com três variáveis, na ordem: assunto, mensagem e host. Revise o
comprimento total no modelo, sem cortar variáveis silenciosamente.

O script de voz mantém os argumentos destino/assunto/mensagem e exige
`NVOIP_CALLER` autorizado. Não reutilize `token_auth`, napikey ou o usertoken
como segredo OAuth. Respostas/erros não imprimem o token nem o corpo do
provedor. Redirecionamentos são recusados. Atualizar arquivos não configura
as actions ou credenciais das instalações: siga o backup e o aceite acima.

Na instalação interna, o ponto de entrada existente `send_sms_nvoip.sh` recebe
este wrapper. A configuração protegida `/etc/zabbix/nvoip-oauth.env` seleciona
`NVOIP_SMS_TEMPLATE_LAYOUT=zabbix` e os três IDs de templates aprovados. O
quarto parâmetro do media type contém nove campos separados por TAB: nome do
evento, host, severidade, ID, data/hora do problema, EVENT.VALUE,
EVENT.UPDATE.STATUS, data/hora da recuperação e data/hora da atualização.
O adaptador segue os limites e a ordem das cinco variáveis do Webhook nativo.
Macros não resolvidas impedem o envio antes do OAuth. Actions, destinatários,
horários e severidades continuam os mesmos. O comando `nvoip_api.py check`
verifica OAuth sem criar mensagem ou chamada.
