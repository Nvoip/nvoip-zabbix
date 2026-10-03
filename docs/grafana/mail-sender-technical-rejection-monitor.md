# Rejeição técnica por template — NN-5258

O dashboard dedicado `nn5258-mail-rejections`, na pasta Nvoip, usa a datasource
MySQL Desenvolvimento (`000000007`). O dashboard anterior `Servidor E-mails`
(`saJohhCIk`) continua acessível pelo link do painel.

A série agrupa hora, template, estado e status. As métricas usam a janela móvel
de 24 horas e classificam como rejeição técnica somente `sent=-1` com
`invalid:*`, `lim:*` ou `processing_failed`. Bounces reais ficam fora do numerador.
As consultas não retornam destinatários, contas, assunto ou corpo.

A regra `nn5258-threshold` dispara quando `technical_rejection_pct_24h > 1`
**ou** `technical_rejections_24h > 20`; compara contagens sem arredondar a taxa.
A regra separada `nn5258-total` corresponde a `technical_rejection_pct_24h = 100`.
Cada consulta de alerta retorna um rótulo de template e uma única medida numérica,
adequada ao alerta multidimensional. As regras são avaliadas a cada cinco minutos.

## Publicação

Execute `python3 tools/grafana/build_nn5258_provisioning.py` para gerar os artefatos.
Use o instalador revisado com um diretório de staging que contenha esses três arquivos.
Ele cria apenas o provider, dashboard e regras desta entrega; faz backup consistente
antes de reiniciar o Grafana e restaura seus próprios arquivos em falha de health.
O provider precisa da extensão `.yaml`, embora o conteúdo JSON seja YAML válido.

O receiver encontrado em produção usa `example@email.com`. As duas regras mantêm
um mute interval próprio, integral, até existir destinatário operacional válido.
O estado dos alertas continua visível no Grafana. Não usar o endereço de exemplo
para teste nem considerar uma entrega de e-mail comprovada.

## Validação

As quatro consultas completas devem passar `PREPARE` em sessão read-only no Aurora.
A fixture MySQL 8/Grafana 11.6.14 testa 1,0005%, exatamente 1%, mais de vinte,
100%, bounce real, template nulo e mensagens fora da janela; SMTP fica desabilitado.
Em produção, conferir os dois UIDs, datasource, painel, avaliação sem erro e mute.

Migration/SQL: none. São consultas SELECT, sem alteração de tabelas.
Passo manual: nenhum para criar os artefatos; configurar destinatário operacional
é necessário para entrega externa de notificações.

Rollback: retirar apenas o provider/dashboard/arquivo de regras NN-5258, provisionar
`deleteRules` para os dois UIDs e remover o mute próprio por `deleteMuteTimes`.
Não restaurar toda a base Grafana sobre alterações concorrentes.
