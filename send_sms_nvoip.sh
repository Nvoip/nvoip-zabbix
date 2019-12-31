#!/bin/bash

#Nvoip

#Copyright (C) 2020 Nvoip Plataforma Telefonia Ltda
#Leandro Campos <https://www.linkedin.com/in/leandro-campos/>
#License https://www.gnu.org/licenses/gpl-3.0.html

#This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by #the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

#You should have received a copy of the GNU General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>.

###Inicio do Script###
# Seu Token da Nvoip. Acesse https://www.nvoip.com.br, crie sua para ter acesso ao seu Token.
# English: Your Nvoip Token. Visit https://www.nvoip.com.br, create yours to have access to your Token.

#$1, $2, $3 e $4 são os parâmetros, em ordem, que você define no seu Servidor Zabbix. O $1 é o número que irá receber a chamada. Você pode reduzir, alterar a ordem ou acrescentar mais parâmetros.
#English: $1, $2, $3 and $4 are parameters, in order, that you set in your Zabbix Server. $ 1 is the number that will receive the call. You can reduce, change the order or add more parameters.

token_auth="{TOKEN NVOIP}"

curl --include \
     --request POST \
     --header "Content-Type: application/json" \
     --header "token_auth: $token_auth" \
     --data-binary "{
    \"celular\":\"$1\",
    \"msg\":\"$2 $3 $4\"
}" \
'https://api.nvoip.com.br/v1/sms'
