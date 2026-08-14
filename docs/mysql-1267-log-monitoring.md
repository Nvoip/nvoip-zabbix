# Alerta de erro MySQL 1267 (NN-4522)

O template `Template Nvoip MySQL 1267 Log Guard` abre evento de severidade
alta quando uma aplicação registra `MySQL ... 1267` ou
`Illegal mix of collations`. Ele não executa SQL, não coleta linhas sem match e
não altera collation, schema, tabela ou dados.

## Ativação

1. Importe `templates/template-nvoip-mysql-1267-log.json` no Zabbix 7.0.
2. Vincule-o somente a hosts produtivos com agente ativo e logs de aplicação.
3. Sobrescreva `{$NVOIP.MYSQL1267.LOG_PATH}` com a expressão absoluta dos logs
   daquele host. Não altere permissões de arquivo para acomodar o agente; use um
   log já legível pelo grupo operacional ou encaminhamento existente.
4. Confirme que o item está suportado e recebe apenas linhas de teste.
5. Associe a trigger à ação operacional existente para Engenharia/Operações.

Para containers cujos logs já vão a CloudWatch, crie um metric filter equivalente
no pipeline existente ou encaminhe o grupo ao Zabbix. Não monte volume de log nem
adicione credencial estática apenas para este alerta.

## Smoke seguro

Em homologação, escreva uma linha sintética contendo
`MySQL error 1267 - Illegal mix of collations` no log monitorado. Isso testa o
pipeline sem executar uma consulta incompatível. O evento deve abrir em até
cinco minutos, identificar host e arquivo e permanecer manualmente fechável.
Remova a linha/arquivo de teste e encerre o evento depois de registrar a
evidência.

## Resposta

1. Identifique serviço, contexto, job e frequência; contenha retry em laço.
2. Consulte tipo, charset e collation dos dois operandos em
   `information_schema.columns` e a collation da conexão.
3. Preserve a semântica: `COLLATE` para texto case/accent-insensitive; `BINARY`
   apenas para igualdade byte a byte comprovada.
4. Compile a consulta completa com `PREPARE` no schema-alvo.
5. Nunca altere as collations das tabelas protegidas como resposta ao alerta.

## Rollback

Desvincule somente este template dos hosts e restaure o export anterior. Não
remova o agente, não mude permissões de logs e não desative outras ações do
Zabbix como parte do rollback.
