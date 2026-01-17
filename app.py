import os
import time
import jwt  # PyJWT
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"

@app.get("/")
def root():
    try:
        # 環境変数の取得（存在しない場合はKeyErrorが発生）
        client_id = os.environ["LINEWORKS_CLIENT_ID"]
        client_secret = os.environ["LINEWORKS_CLIENT_SECRET"]
        service_account_id = os.environ["LINEWORKS_SERVICE_ACCOUNT_ID"]
        # 改行コードの処理をより安全に
        private_key = os.environ["LINEWORKS_PRIVATE_KEY"].replace("\\n", "\n")

        now = int(time.time())

        payload = {
            "iss": client_id,
            "sub": service_account_id,
            "aud": TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
            "scope": "bot" # 利用するスコープに合わせて適宜変更
        }

        # RS256で署名
        assertion = jwt.encode(
            payload,
            private_key,
            algorithm="RS256"
        )
        
        # PyJWTのバージョンにより戻り値がbytesの場合があるための対策
        if isinstance(assertion, bytes):
            assertion = assertion.decode('utf-8')

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        # ヘッダーにContent-Typeを指定（requestsが自動判別するが明示的だと安全）
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        res = requests.post(TOKEN_URL, data=data, headers=headers)
        
        # HTTPエラー（4xx, 5xx）があれば例外を発生させる
        res.raise_for_status()

        return res.json()

    except KeyError as e:
        return {"error": f"環境変数が設定されていません: {str(e)}"}
    except requests.exceptions.RequestException as e:
        # API通信エラーの詳細を返す
        return {
            "error": "LINE WORKS API Request Failed",
            "detail": res.json() if 'res' in locals() else str(e)
        }
    except Exception as e:
        return {"error": f"予期せぬエラー: {str(e)}"}