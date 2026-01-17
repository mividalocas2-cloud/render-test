import os
import time
import jwt
import requests

CLIENT_ID = os.environ["LINEWORKS_CLIENT_ID"]
CLIENT_SECRET = os.environ["LINEWORKS_CLIENT_SECRET"]

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

now = int(time.time())

payload = {
    "iss": CLIENT_ID,
    "sub": CLIENT_ID,
    "aud": TOKEN_URL,
    "iat": now,
    "exp": now + 3600
}

assertion = jwt.encode(
    payload,
    CLIENT_SECRET,
    algorithm="HS256"
)

data = {
    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
    "assertion": assertion
}

res = requests.post(TOKEN_URL, data=data)

print(res.status_code)
print(res.text)
