import os
import time
import json
import jwt
import requests
from fastapi import FastAPI

app = FastAPI()

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

def get_access_token():
    client_id = os.environ["LINEWORKS_CLIENT_ID"]
    private_key_json = os.environ["LINEWORKS_PRIVATE_KEY"]

    key_data = json.loads(private_key_json)

    now = int(time.time())

    payload = {
        "iss": client_id,
        "sub": key_data["client_email"],
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 300
    }

    assertion = jwt.encode(
        payload,
        key_data["private_key"],
        algorithm="RS256"
    )

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion
    }

    res = requests.post(TOKEN_URL, data=data)
    print(res.status_code, res.text)
    res.raise_for_status()

    return res.json()["access_token"]


@app.get("/token-test")
def token_test():
    token = get_access_token()
    return {"access_token": token[:30] + "..."}
