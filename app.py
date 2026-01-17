import os
import requests

CLIENT_ID = os.environ.get("LINEWORKS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINEWORKS_CLIENT_SECRET")

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

data = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "bot"
}

res = requests.post(TOKEN_URL, data=data)

print("status:", res.status_code)
print(res.text)
