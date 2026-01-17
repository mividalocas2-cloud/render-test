import os
import time
import jwt
import requests
from fastapi import FastAPI

app = FastAPI()

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

def get_access_token():
    client_id = os.environ["LINEWORKS_CLIENT_ID"]
    client_secret = os.environ["LINEWORKS_CLIENT_SECRET"]

    now = int(time.time())

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600
    }

    assertion = jwt.encode(
        payload,
        client_secret,
        algorithm="HS256"
    )

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion
    }

    res = requests.post(TOKEN_URL, data=data)
    print(res.status_code)
    print(res.text)
    return res.text


@app.get("/token-test")
def token_test():
    token = get_access_token()
    return {"access_token": token[:30] + "..."}
