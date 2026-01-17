import os
import time
import jwt
import requests

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

def create_jwt():
    private_key = os.environ["LINEWORKS_PRIVATE_KEY"].replace("\\n", "\n")
    client_id = os.environ["LINEWORKS_CLIENT_ID"]

    now = int(time.time())

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )

    return token


def get_access_token():
    assertion = create_jwt()

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
        "client_id": os.environ["LINEWORKS_CLIENT_ID"],
        "client_secret": os.environ["LINEWORKS_CLIENT_SECRET"],
        "scope": "bot"
    }

    res = requests.post(TOKEN_URL, data=data)

    # エラー時に内容を確認できるようにする
    if res.status_code != 200:
        raise Exception(res.text)

    return res.json()
