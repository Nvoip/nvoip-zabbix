# nvoip-zabbix
Scripts para uso com a plataforma Zabbix integrada com a API da Nvoip.

## Intruções
- Para usar os scripts, é necessário ter uma conta e um token válido na Nvoip. Você pode criar sua conta gratuitamente em https://www.nvoip.com.br
- Sinta-se livre para criar e contribuir com os códigos deste repositório. Também fique a vontade para reportar bugs relacionados ao uso da API com a linguagem PHP.
- Acesse https://www.nvoip.com.br/api para acessar a documentação da nossa API.

## Scripts by Nvoip:
### Disparo de SMS Shell Script send_sms_nvoip
Este script irá disparar um SMS quando uma Trigger do Zabbix for acionada. Para isso, é necessário também configurar uma Midia no Zabbix.
Como usar (Testado no Zabbix 3.4): 

1. Copie o arquivo send_sms_nvoip.sh no diretório de Scripts de Alerta do Zabbix (No nosso caso ficou em /usr/lib/zabbix/alertscripts). Para consultar onde é este diretório na sua versão do Zabbix acesse o arquivo zabbix_server.conf (Geralmente em /etc/zabbix/zabbix_server.conf) e procure a linha: AlertScriptPath.
Altere a linha token_auth com o seu Token da Nvoip.

2. Ajuste as permissões do arquivo com os comandos: chown zabbix:zabbix (ou o usuário que definiu pro Zabbix) e chmod 777.

3. Acesse seu Zabbix, vá em Administração > Tipo de Mídia e clique em Criar Tipo de Mídia e use as configurações abaixo:  

Nome: SMS Nvoip  
Tipo: Script  
Nome Script: send_sms_nvoip.sh  
Parâmetro:  
{ALERT.SENDTO}  
{ALERT.SUBJECT}  
{ALERT.MESSAGE}  
{HOST.NAME1}  
Ativo: Sim  

4. Vá em Configurações > Usuários, selecione o usuário que irá receber o SMS. Clique em Mídia, Adicionar. Configure com os dados abaixo:
Tipo: SMS Nvoip
Enviar para: (Coloque aqui o celular que irá receber o SMS (Atualmente somente celulares brasileiros). Formato: DDD+Número. Exemplo: 11911112222.
Ativo quando: 1-7,00:00-24:00 (Ou de acordo com a sua preferência)
Usar se severidade: Marque as opções de severidade da trigger que irá disparar o SMS.
Ativo: Sim

5. Pronto. Agora você irá receber o SMS.

# English Version
PHP language scripts and libraries for use with the Nvoip API.

## Instructions
- To use the scripts, you must have a valid Nvoip account and token. You can create your account for free at https://www.nvoip.com.br
- Feel free to create and contribute code from this repository. Also feel free to report bugs related to the use of the API with the PHP language.
- Visit https://www.nvoip.com.br/api to access our API documentation.

## Scripts by Nvoip:
### SMS Shell Script Trigger send_sms_nvoip
This script will trigger an SMS when a Zabbix Trigger is triggered. For this, it is also necessary to configure a media in Zabbix.
How to use it (Tested on Zabbix 3.4):

1. Copy the send_sms_nvoip.sh file to the Zabbix Alert Scripts directory (In our case it was / usr / lib / zabbix / alertscripts). To see where this directory is in your version of Zabbix go to the zabbix_server.conf file (usually /etc/zabbix/zabbix_server.conf) and look for the line: AlertScriptPath.
Change the token_auth line with your Nvoip Token.

2. Set the file permissions with the commands: chown zabbix: zabbix (or the user who set it for Zabbix) and chmod 777.

3. Access your Zabbix, go to Administration> Media Type and click Create Media Type and use the settings below:

Name: SMS Nvoip  
Type: Script  
Script Name: send_sms_nvoip.sh  
Parameter:  
{ALERT.SENDTO}  
{ALERT.SUBJECT}  
{ALERT.MESSAGE}  
{HOST.NAME1}  
Active: Yes  

4. Go to Settings> Users, select the user who will receive SMS. Click Media, Add. Configure with the data below:
Type: SMS Nvoip
Send to: (Enter here the phone that will receive the SMS (Currently only Brazilian mobile phones.) Format: DDD + Number. Example: 11911112222.
Active when: 1-7,00:00-24:00 (Or according to your preference)
Use if severity: Check the trigger severity options that will trigger SMS.
Active: Yes

5. Ready. You will now receive the SMS.
