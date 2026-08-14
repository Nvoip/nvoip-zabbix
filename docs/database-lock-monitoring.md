# Monitoramento de locks e consultas longas no Aurora

Runbook do NN-4554 para detectar uma fila de metadata lock antes que ela bloqueie o banco compartilhado.

## Escopo e privacidade

O template consulta apenas contagens e idades em `information_schema.PROCESSLIST`. Ele não retorna `INFO`, texto SQL, parâmetros, schema, tabela, IP, usuário de aplicação nem dados de cliente. Não existe ação automática de `KILL`.

Limiar inicial:

- aviso: pelo menos 3 esperas de metadata lock com idade mínima de 30 segundos, sustentadas por 1 minuto;
- desastre: pelo menos 20 esperas ou espera máxima de 120 segundos, sustentadas por 1 minuto;
- consulta longa: aviso acima de 300 segundos e severidade alta acima de 900 segundos;
- indisponibilidade do detector: ausência de amostra por 2 minutos;
- privilégio insuficiente: nenhuma outra sessão visível durante 5 minutos.

Os valores são macros do template e podem ser calibrados com histórico sem editar a consulta.

## Pré-requisitos

1. Zabbix 7.0 com suporte a ODBC.
2. DSN `nvoip` funcional para o serviço `zabbix-server`.
3. Conta dedicada de leitura com o privilégio global `PROCESS`. Esse privilégio revela metadados de sessões; por isso a consulta agregada não coleta identidades nem texto SQL.
4. O grant deve ser aplicado pelo runbook versionado no repositório `Nvoip/bd`, depois de revisar usuário e host reais. O template alerta quando a conta só enxerga a própria conexão.

## Importação e ativação

1. Importe `templates/template-nvoip-aurora-lock-guard.json` em **Data collection → Templates**.
2. Revise as sete macros e mantenha `{$NVOIP.DB.DSN}=nvoip` enquanto esse for o DSN real.
3. Vincule o template ao host lógico `AuroraDB`.
4. Confirme que o item mestre recebe um array JSON a cada 30 segundos.
5. Confirme que `Aurora guard: visible sessions` é maior que zero. Se ficar em zero, não silencie a trigger: corrija o privilégio `PROCESS` da conta dedicada.
6. Verifique que os quatro itens de lock/query são numéricos e suportados.

A importação e o vínculo são publicação de observabilidade. Devem ocorrer em janela controlada, com export do template/host atual como rollback.

## Teste funcional sem indisponibilidade

Faça a simulação somente em banco descartável ou ambiente isolado. Não use o Aurora de produção como gerador de lock.

1. Crie uma tabela de teste InnoDB sem dados de cliente.
2. Na sessão A, abra transação, leia a tabela e mantenha a transação aberta.
3. Na sessão B, execute um DDL sobre a tabela com `SET SESSION lock_wait_timeout=5`.
4. Resultado esperado de prevenção: a sessão B desiste em aproximadamente 5 segundos; uma terceira leitura não fica presa atrás do DDL por tempo prolongado.
5. Para testar o alerta, use temporariamente macros menores no host de teste ou mantenha a espera apenas pelo tempo necessário. Confirme evento e recuperação no Zabbix.
6. Encerre as sessões, remova a tabela de teste e restaure as macros.

Nunca prolongue artificialmente uma fila de metadata lock em produção para testar o monitor.

## Resposta ao alerta

1. Suspenda novas operações de manutenção.
2. Identifique a sessão DDL em espera e a transação que segura o metadata lock.
3. Prefira interromper a operação de manutenção identificada, não sessões de aplicação.
4. Não execute `KILL` automaticamente. Confirme dono, host, assinatura e impacto antes de qualquer intervenção.
5. Para mudança necessária em tabela quente, use o wrapper de `pt-online-schema-change` e o runbook do repositório `Nvoip/bd`.

## Rollback do monitor

1. Desvincule somente `Template Nvoip Aurora Lock Guard` do host `AuroraDB`, preservando histórico se desejado.
2. Restaure o export anterior se outro objeto tiver sido alterado durante a importação.
3. Não remova o DSN nem revogue credenciais compartilhadas como parte desse rollback sem mapear os demais itens ODBC.
