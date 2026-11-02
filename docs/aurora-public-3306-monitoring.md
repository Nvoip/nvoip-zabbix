# Regra pública na porta do Aurora

NN-6738. Avisa quando uma regra de origem pública volta a alcançar a porta 3306 do cluster `nvoip`. Desde 02/11/2026 o acesso externo está fechado por decisão de Leandro: entram só a VPN e os servidores internos.

## Como funciona

- O timer `nvoip-aurora-public-3306.timer`, no host do Zabbix, roda a cada 5 minutos.
- O coletor `/etc/nvoip/monitoring/aurora_public_3306_check.py` lê os grupos de segurança ligados às instâncias do cluster. Um grupo novo ligado ao banco entra na verificação sem configuração.
- Os valores vão para itens trapper do `Template Nvoip Aurora Public Access`, vinculado ao host lógico `AuroraDB`, e só são aceitos a partir de `127.0.0.1`.

O coletor só lê a AWS. Nenhum trigger altera regra.

## O que conta como pública

Qualquer origem fora de `172.31.0.0/16` que alcance a porta, incluindo regra de todo o tráfego, faixa de portas, IPv6 e prefix list. Regras privadas, referências a outros grupos e regras em outras portas não contam.

## Alertas

| Alerta | Severidade | O que fazer |
| --- | --- | --- |
| Aurora com regra pública na porta do banco | Alta | Veja grupo e origem no item de detalhe e quem criou no CloudTrail. Remova a regra se não houver autorização de Leandro. |
| Coletor das regras públicas do Aurora sem dados | Média | Veja `systemctl status nvoip-aurora-public-3306.service` e a política IAM abaixo. Sem coleta por 30 minutos, uma regra pública passaria despercebida. |

Os dois saem pela ação de e-mail do grupo Zabbix administrators. O item `publicly_accessible` é só informativo: o IP público da instância foi mantido por decisão de Leandro.

## Permissão

O papel `NvoipMonitorSSMCore` tem a política inline `NvoipMonitorAuroraPublicAccessRead`, com `ec2:DescribeSecurityGroups` e `rds:DescribeDBInstances`. Nada além de leitura.

## Publicação

1. Instale o script em `/etc/nvoip/monitoring/` e as units de `deploy/systemd/` em `/etc/systemd/system/`.
2. Importe `templates/template-nvoip-aurora-public-access.json` criando e atualizando objetos, sem a opção de exclusão.
3. Vincule o template somente ao host `AuroraDB` e habilite o timer.

## Teste sem tocar no banco

Use um grupo de segurança temporário, sem anexo, e um host de teste com o template:

```sh
sudo -u zabbix python3 /etc/nvoip/monitoring/aurora_public_3306_check.py \
  --security-group <grupo-temporario> --zabbix-host <host-de-teste>
```

Use origens de documentação como `203.0.113.10/32`. Nunca adicione regra pública aos grupos do Aurora para testar. O teste envia e-mail real aos administradores.

## Rollback

1. `systemctl disable --now nvoip-aurora-public-3306.timer`
2. Desvincule e limpe o template do host `AuroraDB`.
3. `aws iam delete-role-policy --role-name NvoipMonitorSSMCore --policy-name NvoipMonitorAuroraPublicAccessRead`
