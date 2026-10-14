# Monitoramento de memória da API Java (NN-6146)

Este pacote fecha a lacuna de observabilidade identificada no NN-6146. Ele
coleta, a cada minuto, somente métricas agregadas do host e dos Tomcats 9 e 10:

- memória disponível e swap usado no host;
- RSS, Metaspace e ocupação da old generation por Tomcat;
- contagem e tempo acumulado de Full GC;
- classes carregadas e descarregadas.

Não são coletados argumentos completos da JVM, variáveis de ambiente, logs,
requisições, SQL nem dados de clientes. O coletor não força GC, não reinicia
serviços e não altera parâmetros das JVMs.

## Desenho

Os Tomcats produtivos rodam como `root`. Por isso, um serviço `oneshot` também
executado como `root` usa `jstat`, grava JSON atômico e sem segredos em
`/run/nvoip-api-memory/metrics.json` com modo `0644`, e termina. O agente
Zabbix lê o arquivo com a chave nativa `vfs.file.contents`; não recebe `sudo`,
capabilities nem permissão para anexar à JVM.

O timer mantém uma amostra por minuto. O timestamp fica dentro do JSON para o
Zabbix detectar arquivo parado mesmo que o agente continue lendo a última
amostra.

## Limites iniciais

Os valores padrão partem das medições do incidente de 12/10/2026 e devem ser
revisados depois de uma semana de tendência:

| Métrica | Aviso | Alto |
| --- | ---: | ---: |
| Memória disponível | abaixo de 900 MiB por 10 min | abaixo de 650 MiB por 5 min |
| Swap usado | acima de 512 MiB por 15 min | acima de 1 GiB por 10 min |
| Metaspace Tomcat 9 | acima de 700 MiB por 10 min | acima de 1 GiB por 5 min |
| Metaspace Tomcat 10 | acima de 500 MiB por 10 min | acima de 768 MiB por 5 min |
| Classes carregadas | acima de 180 mil por 10 min | acima de 240 mil por 5 min |

O limite alto de memória disponível fica deliberadamente acima da trava de
deploy de 600 MiB. Nenhum trigger executa ação automática.

## Instalação no host da API

Esta é uma etapa de publicação separada do PR. Antes de executá-la, confirmar
o host `Debian 12 - API Java 17`, ausência de deploy concorrente e o rollback.
Não é necessário reiniciar Tomcat 9, Tomcat 10 nem o agente Zabbix.

```sh
sudo install -o root -g root -m 0755 \
  Scripts/nvoip_api_memory_collector.py \
  /usr/local/libexec/nvoip_api_memory_collector.py
sudo install -o root -g root -m 0644 \
  systemd/nvoip-api-memory-collector.service \
  /etc/systemd/system/nvoip-api-memory-collector.service
sudo install -o root -g root -m 0644 \
  systemd/nvoip-api-memory-collector.timer \
  /etc/systemd/system/nvoip-api-memory-collector.timer
sudo systemd-analyze verify \
  /etc/systemd/system/nvoip-api-memory-collector.service \
  /etc/systemd/system/nvoip-api-memory-collector.timer
sudo systemctl daemon-reload
sudo systemctl enable --now nvoip-api-memory-collector.timer
sudo systemctl start nvoip-api-memory-collector.service
```

Os três arquivos de destino são novos. A publicação não deve mudar dono ou
modo de arquivos já existentes.

## Importação no Zabbix

1. Importe `templates/template-nvoip-api-jvm-memory.json` no Zabbix 7.
2. Vincule `Template Nvoip API JVM Memory` somente ao host `Servidor API`.
3. Não habilite ação de restart, GC ou comunicação externa para estes triggers.
4. Aguarde três amostras e confirme em **Monitoring > Latest data** os itens
   `nvoip.api.*` dos dois Tomcats.

Importar e vincular o template altera o monitoramento produtivo e, portanto,
continua sendo passo manual da publicação. A importação não muda SG, Tomcat,
JVM ou permissões de arquivos existentes.

## Validação de produção

Depois da instalação:

```sh
sudo systemctl is-active nvoip-api-memory-collector.timer
sudo systemctl status --no-pager nvoip-api-memory-collector.service
sudo python3 -m json.tool /run/nvoip-api-memory/metrics.json >/dev/null
stat -c '%U:%G %a %n' /run/nvoip-api-memory/metrics.json
```

Resultado esperado:

- timer ativo e último serviço concluído com `status=0/SUCCESS`;
- JSON válido, modo `644`, sem argumentos, segredos ou dados de cliente;
- amostras novas a cada minuto no Zabbix;
- trigger de coletor obsoleto fechado;
- endpoints `/v2/`, `/v3/` e `/auth/` mantendo suas respostas esperadas;
- nenhum restart de JVM no período da instalação.

Para provar a expressão dos triggers sem gerar comunicação real, clone o
template em um host de teste isolado, sem actions, e reduza temporariamente as
macros nesse host. Não reduza limites nem force pressão de memória no host
produtivo.

## Rollback

1. Desvincule o template do host `Servidor API` preservando o histórico, caso
   a interface ofereça essa opção.
2. Desative e remova somente o timer e o serviço do NN-6146:

```sh
sudo systemctl disable --now nvoip-api-memory-collector.timer
sudo rm /etc/systemd/system/nvoip-api-memory-collector.timer
sudo rm /etc/systemd/system/nvoip-api-memory-collector.service
sudo rm /usr/local/libexec/nvoip_api_memory_collector.py
sudo systemctl daemon-reload
sudo rm -rf /run/nvoip-api-memory
```

O rollback não reinicia Tomcat, não limpa swap e não altera JVM. A remoção dos
arquivos deve mirar apenas os caminhos explícitos acima.
