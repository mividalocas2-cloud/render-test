import os
import time
import jwt
import requests

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

client_id = os.environ["LINEWORKS_CLIENT_ID"]
client_secret = os.environ["LINEWORKS_CLIENT_SECRET"]
service_account_id = os.environ["LINEWORKS_SERVICE_ACCOUNT_ID"]
private_key = os.environ["LINEWORKS_PRIVATE_KEY"].replace("\\n", "\n")

now = int(time.time())

payload = {
    "iss": service_account_id,
    "sub": service_account_id,
    "aud": TOKEN_URL,
    "iat": now,
    "exp": now + 3600,
    "scope": "bot"
}

jwt_assertion = jwt.encode(
    payload,
    private_key,
    algorithm="RS256"
)

data = {
    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
    "assertion": jwt_assertion,
    "client_id": client_id,
    "client_secret": client_secret,
}

res = requests.post(TOKEN_URL, data=data)
print(res.status_code)
print(res.text)
