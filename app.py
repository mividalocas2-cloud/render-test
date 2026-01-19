import os
import time
import jwt
import requests
from fastapi import FastAPI

app = FastAPI()

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

@app.get("/")
def root():
    try:
        # 1. 環境変数の読み込み
        client_id = os.environ["LINEWORKS_CLIENT_ID"]
        client_secret = os.environ["LINEWORKS_CLIENT_SECRET"]
        service_account_id = os.environ["LINEWORKS_SERVICE_ACCOUNT_ID"]
        private_key = os.environ["LINEWORKS_PRIVATE_KEY"].replace("\\n", "\n")
        bot_id = os.environ["LINEWORKS_BOT_ID"]
        # 送信先のユーザーID（テスト用に自分のIDを環境変数に入れるか直接記述）
        target_user_id = os.environ.get("USER_ID", "toshiya.goto@works-826009")

        now = int(time.time())

        # 2. JWT (Assertion) の作成
        payload = {
            "iss": client_id,
            "sub": service_account_id,
            "iat": now,
            "exp": now + 3600
        }
        assertion = jwt.encode(payload, private_key, algorithm="RS256")

        # 3. アクセストークンの取得
        token_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "bot bot.message bot.read"
        }
        token_res = requests.post(TOKEN_URL, data=token_data)
        token_res.raise_for_status()
        access_token = token_res.json().get("access_token")

        # 送信先URL: 
        # 修正：ドメインを api.worksmobile.com に変更
        send_url = f"https://api.worksmobile.com/v2/bot/{bot_id}/users/{target_user_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        message_payload = {
            "content": {
                "type": "text",
                "text": "こんにちは！APIからのメッセージ送信に成功しました！"
            }
        }
        
        send_res = requests.post(send_url, json=message_payload, headers=headers)

        return {
            "auth_status": "Success",
            "send_status_code": send_res.status_code,
            "send_response": send_res.json() if send_res.status_code == 201 else send_res.text
        }

    except Exception as e:
        return {"error": str(e)}