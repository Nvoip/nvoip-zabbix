# Alertas das rotas de push do softphone (NN-6117)

O template `Template Nvoip Softphone Push Route Guard` acompanha separadamente
`/nvoip-softphone/push/chat-message` e `/incoming-call`. Ele alerta para 5xx
de qualquer origem, 499 de produtores internos e, em janela de 15 minutos,
quando ao menos metade das respostas aos produtores internos é 4xx. Uma única
requisição interna com 403 já pode abrir o evento; isso teria revelado a
regressão que interrompeu o push de chat. O template não envia push ou chamadas.

## NodeJS Devs

O Nginx versionado em `nvoip-softphone-push/deploy/nginx-softphone-push.conf`
gera `/var/log/nvoip-softphone-push/access.log` com apenas horário, caminho
normalizado, status HTTP e marcador `0/1` de origem interna. Não registra IP,
query string, token nem payload nesse log. O acesso completo existente em
`/var/log/nginx/access.log` continua ativo. A classe interna cobre a VPC do
Chat e as origens de chamada conhecidas; atualize-a quando uma origem mudar.

Na publicação autorizada, crie **novos** diretório e arquivo com acesso restrito
ao agente Zabbix. Não altere permissões dos logs ou arquivos preexistentes:

```sh
sudo install -d -o root -g zabbix -m 0750 /var/log/nvoip-softphone-push
sudo install -o www-data -g zabbix -m 0640 /dev/null /var/log/nvoip-softphone-push/access.log
sudo install -o root -g root -m 0644 deploy/logrotate-softphone-push-monitor.conf /etc/logrotate.d/nvoip-softphone-push-monitor
sudo nginx -t
```

Esses comandos são roteiro de publicação, não parte dos testes em bancada.
Compare a configuração ativa antes de substituir o arquivo Nginx e valide o
rollback. Confirme que `sudo -u zabbix test -r` consegue ler o **novo** log,
inclusive depois da primeira rotação; o logrotate dedicado usa
`www-data:zabbix 0640`. Uma falha de leitura deve aparecer como item não
suportado, nunca como série silenciosamente saudável.

## Servidor Zabbix

1. Importe `templates/template-nvoip-softphone-push-routes.json` no Zabbix 7.0
   e vincule-o apenas ao host produtivo de NodeJS Devs com agente ativo.
2. Confirme que os dois itens `logrt` estão suportados e recebem os estados
   das rotas; a macro aponta para o log dedicado e seus arquivos rotacionados.
3. Vincule as quatro triggers à ação operacional interna apropriada. Confira
   destinatário, janela e recuperação sem criar SMS, WhatsApp ou chamada de
   teste para clientes.
4. Em bancada, alimente um log sintético com `chat-message 403 1`,
   `incoming-call 503 1` e respostas 200. Confirme separadamente a razão de
   4xx e o disparo de 5xx/499; depois remova o template da bancada.
5. Em produção, acompanhe o primeiro tráfego real e confirme que as métricas
   chegam ao host correto. `healthz` e importação do template não provam que a
   notificação da ação foi entregue.

As linhas de status do Nginx mostram a resposta HTTP, não o resultado do
provedor. Para um push que recebeu HTTP 200 depois de o Chat desistir,
correlacione `chat_push_processed.sent`/`failed` no serviço. Ações que enviem
comunicações externas requerem os destinos operacionais já autorizados.

## Reversão

Desvincule apenas este template e restaure o arquivo Nginx anterior se a
telemetria causar impacto. Preserve os logs para diagnóstico e não altere o
agente, outros templates ou permissões de arquivos existentes.
