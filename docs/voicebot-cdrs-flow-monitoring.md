# Voicebot e cdrs_flow no Zabbix (NN-6660)

## Estado aplicado em 01/11/2026

O Zabbix 7.0 monitora os hosts `Servidor Cronjobs`, `nvoip-fs-ura-voicebot-prod`,
`Servidor NodeJS Devs` e `Zabbix server`. Os itens `cdrs_flow:` leem apenas a
linha agregada `FIM:` do log do sincronizador. `no_match` recente é tendência;
não cria incidente. O item `ORPHAN S3 FAIL` detecta falha de preservação. O
coletor abaixo usa a conexão Aurora já existente no CronJobs e publica somente
cinco números. Não fornece conta, UUID, `id_astpp`, JSON, chave S3 ou destino.

O host CronJobs precisou de `ServerActive=172.31.46.164`, IP privado do mesmo
Zabbix, porque a porta 10051 do endereço público não era alcançável a partir
dele. O backup anterior fica em
`/etc/zabbix/zabbix_agentd.conf.bak_codex_cdrs_flow_20261101`. Apenas
`zabbix-agent` foi reiniciado; dono e modo da configuração foram preservados.

## Coletor de total e idade

Fonte: [`../Scripts/cdrs_flow_metrics.lua`](../Scripts/cdrs_flow_metrics.lua).
Executar como root no CronJobs, com Lua 5.1 e o contrato existente
`/etc/nvoip/database-configuration/db-att.lua`. A consulta é `SELECT` puro,
em sessão read-only e com `max_execution_time=3000`; usa o índice
`idx_created_at`. Em 01/11, o `EXPLAIN` leu 5 linhas e uma execução real
retornou total 5, idade máxima 59.265 s, zero acima de 24 h e 3 criadas
nos últimos 5 min. O custo deve ser revisto se o buffer crescer.

Instalar o script em `/etc/nvoip/monitoring/cdrs_flow_metrics.lua` e criar
somente o diretório de saída `/var/lib/nvoip-zabbix`. O arquivo novo
`/etc/cron.d/nn6660-cdrs-flow-metrics` deve executar a cada 5 min e publicar
atomicamente em `/var/lib/nvoip-zabbix/cdrs_flow.metrics`, com um temporário
seguido de `mv` somente após exit 0. Na falha, o arquivo anterior fica intacto
e `updated_epoch` envelhece. O agente lê o arquivo com `vfs.file.regexp[]`;
nenhuma credencial é dada ao usuário `zabbix`.

## Gatilhos e triagem

- `cdrs_flow`: ausência de ciclo por 10 min; falhas em ciclos consecutivos;
  `ORPHAN S3 FAIL`; 100 órfãos arquivados em um ciclo. A soma de deleções por
  janela indica ritmo de drenagem. Para backlog, conferir total,
  `oldest_age_seconds` e `overdue_24h` juntos antes de atuar.
- Flow/Voicebot: projetor ou publicador abaixo da contagem esperada; linhas
  ativas stale/expiradas por 5 min; FreeSWITCH, gateways e timers inativos.
  O status do coletor e os gatilhos CCV2 anteriores continuam valendo.
- Softphone-push: `healthz` HTTPS público exige HTTP 200, cadeia e hostname TLS
  válidos; certificado alerta com 21 dias de antecedência e leitura ausente
  por 3 h. O `certbot.timer` continua responsável pela renovação.
- `no_match` recente, snapshots vazios isolados, `TRIGGER_NOT_FOUND` e
  `ASSET_SOURCE_UNAVAILABLE` sem efeito correlacionado são contexto funcional
  ou transitório. `FLOW_QUEUE_FAILURE_FALLBACK_FAILED` merece investigação
  pontual por chamada, sem inferir indisponibilidade sistêmica.

A ação padrão `Report problems to Zabbix administrators` envia e-mail ao
administrador configurado e recuperação ao fechar o incidente. Em 01/11, o
log de ações marcou envios recentes como `sent`; isso confirma o transporte
do Zabbix, não leitura humana da mensagem. Antes de pausar a validação diária
do Codex, conferir coleta do arquivo agregado, gatilhos, notificação e
recuperação com um teste controlado que não crie efeito em cliente.

## Contenção e rollback

Desabilitar somente os itens/gatilhos NN-6660, remover o novo arquivo cron e
o script, preservando o arquivo de métricas e histórico de eventos para
diagnóstico. Se a rota ativa falhar, restaurar o backup exato da configuração
do agente e reiniciar somente `zabbix-agent`. Não reiniciar FreeSWITCH, Flow,
Redis ou o sincronizador, nem alterar banco, SG ou permissões existentes para
contornar um alerta.
