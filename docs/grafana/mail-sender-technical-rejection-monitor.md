# Monitor de rejeição técnica por template (NN-5258)

Alvo: dashboard Grafana `Servidor E-mails` (`saJohhCIk`), datasource
`Desenvolvimento` (`000000007`, MySQL), sem criar uma notificação real nesta
entrega. A auditoria somente leitura confirmou que os painéis 2, 4 e 8 desse
dashboard já consultam `desenvolvimento.mail_sender`.

`mail-sender-technical-rejection-series.sql` fornece a série por template e
`status_bounce`. `mail-sender-technical-rejection-alerts.sql` fornece um valor
por template para as regras. Ambas usam a janela móvel de 24 horas e classificam
como rejeição técnica somente `sent = -1` com `invalid:%`, `lim:%` ou
`processing_failed`. Outros bounces e estados permanecem visíveis na série,
mas não contam no numerador.

## Configuração manual no Grafana

1. Faça backup do JSON atual do dashboard `saJohhCIk` e registre a versão.
2. Crie um painel de tabela ou barras com
   `mail-sender-technical-rejection-series.sql`; use `template_id` e
   `status_bounce` como dimensões e `messages_with_status_24h` como valor.
3. Crie uma regra de alerta multi-dimensional usando a consulta de alertas. Por
   `template_id`, dispare quando
   `technical_rejection_pct_24h > 1` **ou** `technical_rejections_24h > 20`.
4. Crie outra regra, separada da anterior, para o mesmo conjunto de séries:
   dispare quando `technical_rejection_pct_24h = 100`. Mantenha-a separada
   para identificar perda integral de um template mesmo quando o volume for
   menor que 20.
5. Inicialmente deixe ambas as regras sem contact point; valide o preview com
   dados de produção somente leitura e então associe a política de notificação
   autorizada pelo responsável operacional.

## Publicação e rollback

Esta alteração apenas versiona SQL e o roteiro; não altera Grafana nem envia
notificações. A publicação exige aplicar manualmente os dois painéis/regras no
Grafana. O rollback é restaurar o JSON salvo do dashboard e remover as duas
regras pelo UID criado na publicação.

Migration/SQL: none. As consultas são `SELECT` somente leitura contra
`desenvolvimento.mail_sender`; não há migration.

Passo manual: configurar painel e regras no Grafana após revisão.
