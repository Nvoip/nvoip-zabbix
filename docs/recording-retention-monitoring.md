# Monitoramento de retenção de gravações (NN-2350 / NN-4830)

Este monitor substitui o acompanhamento operacional recorrente no chat. O
Zabbix alerta falhas e decisões necessárias; métricas de produto como abertura,
clique por CTA, reativação e atribuição causal continuam em BI/Grafana quando
houver telemetria correlacionável.

## O que é monitorado

No host `Servidor Cronjobs`, o template
`Template Nvoip Recording Retention CronJobs` observa somente:

- o resumo agregado diário de `account_recording_retention`;
- o marcador `s3_lgpd skipped reason=retention_only`;
- atualização do log, CRC32 do Lua ativo e quantidade de processos do worker;
- `failed>0`, execução duplicada ou fora da janela normal e o alerta crítico
  `deletion_enabled=true` da flag legada.

O item de log não aceita linhas com conta, e-mail, objeto, versão ou destinatário.
O CRC32 existe porque o agente legado não suporta `vfs.file.cksum[...,sha256]`;
o SHA-256 do recibo de deploy continua sendo a fonte de verdade.

No host lógico `AuroraDB`, o template
`Template Nvoip Recording Retention Database` executa a cada dois minutos uma
única consulta `SELECT` agregada. Ela mede:

- aprovação operacional ativa e tempo até expirar;
- intents `PREPARED/STARTED` e idade do mais antigo;
- candidatos vencidos ainda não drenados;
- versões exatas excluídas e eventos `VERSION_DELETED` em cinco minutos;
- divergências entre intent `DELETED` e `gone_at`;
- legal holds ativos;
- filas do template 266 pendentes há mais de 30 minutos e falhas/bounces na
  última hora, excluindo os quatro testes conhecidos e a conta interna.

A consulta não retorna `id_astpp`, Numbersip, usuário, e-mail, chave S3,
`version_id` nem conteúdo de mensagem. `sent=2` não é tratado como entrega.

## Limites iniciais

- aprovação: alerta alto se ausente/expirada e aviso sete dias antes do prazo;
- intent incerto: desastre após cinco minutos em `PREPARED/STARTED`;
- candidato não drenado: alto após dez minutos;
- vazão: desastre acima de seis exclusões confirmadas em uma janela de cinco
  minutos, incompatível com o envelope produtivo batch 1 / ciclo de um minuto;
- worker CronJobs: alto quando ainda roda depois das 07:00 ou antes das 03:59,
  desastre se houver mais de um processo;
- resumo/marcador diário: alerta após 26 horas sem nova amostra;
- aviso 266: alto quando pendente por mais de 30 minutos; warning para
  falha/bounce real na última hora.

`warned=0`, `deferred>0`, zero candidatos e legal hold ativo não são falhas por
si só. Nenhum trigger executa rollback, renova aprovação, muda flag, reenvia
e-mail, chama cliente, altera banco ou apaga objeto.

## Publicação

1. Importe os dois JSONs de `templates/` no Zabbix 7.0 usando atualização de
   objetos existentes e criação de novos; não use a opção de exclusão.
2. Vincule o template CronJobs somente ao host `Servidor Cronjobs`.
3. Vincule o template de banco somente ao host `AuroraDB`, que já possui o DSN
   read-only `nvoip`.
4. Confirme que o item ODBC mestre retorna um array JSON com uma linha e que
   todos os dependentes ficam suportados.
5. Use checks passivos para o CronJobs. O `Server` do agente deve aceitar o IP
   privado do Zabbix já usado pela rede interna; não abra `10051`, não amplie SG
   e não altere permissões: o log e o Lua já são legíveis pelo usuário
   `zabbix`.
6. Revise as ações internas associadas às severidades. Não faça SMS, WhatsApp,
   ligação ou e-mail de teste para cliente.

A consulta exata fica em
`docs/sql/nn2350-recording-retention-health.sql`. Antes de importar, compile-a
por `PREPARE` e execute uma única vez em sessão read-only com teto de três
segundos no schema `desenvolvimento`.

## Resposta aos alertas

- **flag legada habilitada:** tratar como crítico. Confirmar ambiente e comando
  do cron, conter a execução futura e reconciliar o último ciclo. Não confundir
  com as flags do scheduler exato do Backend.
- **intent preso/divergência física:** inativar a aprovação operacional pelo
  procedimento NN-4830 e reconciliar intent, `gone_at`, evento e a versão S3
  exata. Nunca repetir por chave sem `versionId`.
- **candidato não drenado/aprovação expirada:** validar flags do runtime,
  aprovação e log `[NN-4830] exact-version retention`. Não alterar datas para
  fabricar elegibilidade.
- **worker longo/duplicado:** identificar o dono do `flock`, processo filho e
  última linha agregada. Não iniciar segundo ciclo e não matar processo sem
  entender se existe efeito externo incerto.
- **fila/falha 266:** inspecionar o worker de e-mail e eventos do provedor.
  Aceite do provedor (`sent=2`) não prova entrega.

## Rollback

Desvincule somente os dois templates dos respectivos hosts, preservando o
histórico se necessário. Se a importação atualizou um objeto preexistente,
restaure o export feito imediatamente antes da publicação. Não remova o DSN,
remova somente o IP privado acrescentado a `Server` no agente do CronJobs e não
mude permissões de log como parte do rollback.
