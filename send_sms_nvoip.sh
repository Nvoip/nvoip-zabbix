#!/bin/bash
# Seu usuario
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
