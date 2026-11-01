# Monitoramento de retenção de gravações (NN-2350 / NN-4830 / NN-6673)

Este monitor substitui o acompanhamento operacional recorrente no chat. O
Zabbix alerta falhas e decisões necessárias; métricas de produto como abertura,
clique por CTA, reativação e atribuição causal continuam em BI/Grafana quando
houver telemetria correlacionável.

## O que é monitorado

No host `Servidor Cronjobs`, o template
`Template Nvoip Recording Retention CronJobs` observa somente:

- o resumo agregado diário de `account_recording_retention`;
- o marcador `s3_lgpd skipped reason=retention_only`;
- o resumo agregado de uma limpeza real de contas encerradas (`s3_lgpd selected=`
  com `dry_run=false`), produzido pelo modo `--lgpd-only` (NN-6673);
- atualização do log, CRC32 do Lua ativo e quantidade de processos do worker;
- `failed>0`, execução duplicada ou fora da janela normal e o alerta crítico
  `deletion_enabled=true` da flag legada.

O item de log não aceita linhas com conta, e-mail, objeto, versão ou destinatário.
Os itens usam o modo `skip`: a publicação começa no fim do arquivo e não
reprocessa o histórico como se fossem eventos atuais.
O CRC32 existe porque o agente legado não suporta `vfs.file.cksum[...,sha256]`;
o SHA-256 do recibo de deploy continua sendo a fonte de verdade.

O modo `--lgpd-only` imprime `account_recording_retention skipped reason=lgpd_only`.
Essa linha não casa com o resumo da retenção nem com o marcador, e o processo
`--lgpd-only` não entra em `proc.num[...--retention-only]`: os gatilhos desses três
itens continuam medindo só a linha das 04:00.

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
- limpeza LGPD: alto após 26 horas sem resumo real e com `failed>0`. A simulação
  (`dry_run=true`) não conta como execução: um `--dry-run` deixado no cron também
  dispara o alerta;
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
5. Use checks ativos para os dois itens `log[]` e checks passivos para processo,
   CRC32 e mtime. `ServerActive` deve apontar para o IP privado do Zabbix e
   `Server` deve aceitar esse mesmo IP privado. Não publique `10051`, não amplie
   SG e não altere permissões: o log e o Lua já são legíveis pelo usuário
   `zabbix`.
6. Revise as ações internas associadas às severidades. Não faça SMS, WhatsApp,
   ligação ou e-mail de teste para cliente.

A consulta exata fica em
`docs/sql/nn2350-recording-retention-health.sql`. Antes de importar, compile-a
por `PREPARE` e execute uma única vez em sessão read-only com teto de três
segundos no schema `desenvolvimento`.

### Atualizar o CRC32 depois de publicar o Lua

O valor aprovado é a macro `{$NVOIP.RETENTION.SCRIPT.CRC32}`, versionada no template
do CronJobs. Ela muda a cada publicação de `s3_delete_recordings-v3.lua`:

1. Publique o Lua pela esteira do `api-cronjobs` e confira no CronJobs, só leitura:
   `sha256sum` e `cksum` de `/etc/nvoip/maintenance/s3_delete_recordings-v3.lua`. O
   primeiro campo do `cksum` é o valor que o agente reporta; os dois devem bater com
   o template deste repositório.
2. Mescle o PR do template e importe
   `templates/template-nvoip-recording-retention-cronjobs.json` em
   *Coleta de dados > Modelos > Importar*, criando e atualizando objetos e sem a opção
   de exclusão. Faça isso logo depois do passo 1.
3. O item de CRC32 coleta a cada 15 minutos. Se a coleta cair entre os dois passos, o
   alerta alto de artefato divergente abre; depois da importação ele se resolve na
   coleta seguinte, ou feche manualmente com o recibo do deploy.

Publicar o Lua sem importar o template mantém esse alerta aberto; importar antes de
publicar também o abre. O valor do template só vale para o SHA-256 da sua descrição.

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
- **limpeza LGPD sem resumo:** a linha `--lgpd-only` das 22:30 tem lock próprio
  (`/etc/nvoip/lockfiles/s3_delete_recordings-v3-lgpd.lock`), separado do lock da
  retenção das 04:00. Ver se uma execução anterior ainda segura esse lock (`flock -n`
  pula sem registrar nada) e conferir no crontab root se a linha existe e está sem
  `--dry-run`. A fila espera a execução seguinte; não iniciar segundo ciclo.
- **limpeza LGPD com falha:** ler as linhas `s3_cleanup=failed` no log, sem exportar
  conta. O estado local e os lotes já concluídos são preservados; a próxima execução
  retoma sozinha.
- **fila/falha 266:** inspecionar o worker de e-mail e eventos do provedor.
  Aceite do provedor (`sent=2`) não prova entrega.

## Rollback

Desvincule somente os dois templates dos respectivos hosts, preservando o
histórico se necessário. Se a importação atualizou um objeto preexistente,
restaure o export feito imediatamente antes da publicação. Não remova o DSN;
restaure os valores anteriores de `Server` e `ServerActive` no agente do
CronJobs e não mude permissões de log como parte do rollback.
