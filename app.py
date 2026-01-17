import os
import time
import json
import base64
import jwt
import requests

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

def get_access_token():
    client_id = os.environ["LINEWORKS_CLIENT_ID"]

    key_b64 = os.environ["LINEWORKS_PRIVATE_KEY_B64"]
    key_json = base64.b64decode(key_b64).decode("utf-8")
    key_data = json.loads(key_json)

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
