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

# 1. JWTのPayload (Claims Set) - ドキュメント通り iss, sub, iat, exp のみ
        payload = {
            "iss": client_id,
            "sub": service_account_id,
            "iat": now,
            "exp": now + 3600
            # ※ここに scope を入れない構成でもドキュメント上はOKですが、
            # LINE WORKS V2では含めてもエラーにはなりません。
        }

        # 2. JWTの生成 (Headerはjwtライブラリが自動付与)
        assertion = jwt.encode(
            payload,
            private_key,
            algorithm="RS256"
        )

        # 3. POSTデータの作成 - ここで scope を明示的に送る
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "client_id": client_id,
            "client_secret": client_secret,
            # ここにスペース区切りで並べる
            "scope": "bot bot.message bot.read" 
        }

        # 4. リクエスト送信
        res = requests.post(TOKEN_URL, data=data)

        # ヘッダーにContent-Typeを指定（requestsが自動判別するが明示的だと安全）
        #headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        #res = requests.post(TOKEN_URL, data=data, headers=headers)
        
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