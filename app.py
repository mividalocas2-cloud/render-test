import os
import time
import jwt
import requests
import psycopg2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates

app = FastAPI()
# 1. 環境変数の読み込み
client_id = os.environ["LINEWORKS_CLIENT_ID"]
client_secret = os.environ["LINEWORKS_CLIENT_SECRET"]
service_account_id = os.environ["LINEWORKS_SERVICE_ACCOUNT_ID"]
private_key = os.environ["LINEWORKS_PRIVATE_KEY"].replace("\\n", "\n")
bot_id = os.environ["LINEWORKS_BOT_ID"]
target_user_id = "toshiya.goto@works-826009"
templates = Jinja2Templates(directory="templates")

TOKEN_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"
DATABASE_URL = os.environ["DATABASE_URL"]

# ==============================
# database
# ==============================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def send_bot_message(message_text: str, target_user_id: str = None):
    """
    LINE WORKS Botでメッセージを送信する共通関数
    """
    try:
        
        # 送信先が指定されていない場合はデフォルト（承認者など）を使用
        if not target_user_id:
            target_user_id = "toshiya.goto@works-826009"

        # 2. JWTの生成
        now = int(time.time())
        payload = {
            "iss": client_id,
            "sub": service_account_id,
            "iat": now,
            "exp": now + 3600
        }
        assertion = jwt.encode(payload, private_key, algorithm="RS256")

        # 3. アクセストークンの取得
        token_url = "https://auth.worksmobile.com/oauth2/v2.0/token"
        token_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "bot bot.message bot.read"
        }
        token_res = requests.post(token_url, data=token_data)
        token_res.raise_for_status()
        access_token = token_res.json().get("access_token")

        # 4. メッセージの送信 (成功したURL形式を使用)
        send_url = f"https://www.worksapis.com/v1.0/bots/{bot_id}/users/{target_user_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        message_payload = {
            "content": {
                "type": "text",
                "text": message_text
            }
        }
        
        # 送信実行
        res = requests.post(send_url, json=message_payload, headers=headers)
        return res.status_code

    except Exception as e:
        print(f"Bot送信エラー詳細: {e}")
        return None

@app.get("/")
def root():
        return RedirectResponse(url="/form")

@app.get("/form", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.post("/confirm", response_class=HTMLResponse)
def confirm(
    request: Request,
    name: str = Form(...),
    department: str = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    days: str = Form(...),
    reason: str = Form(...),
    other_reason: str = Form(""),
    vacation_type: str = Form(...),
    note: str = Form("")
):
    return templates.TemplateResponse(
        "confirm.html",
        locals()
    )


@app.post("/complete", response_class=HTMLResponse)
def complete(
    request: Request,
    department: str = Form(...),
    name: str = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    days: int = Form(...),
    reason: str = Form(...),
    other_reason: str = Form(""),
    vacation_type: str = Form(...),
    note: str = Form("")
):
    # 1. データベース保存（既存のコード）
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO leave_requests
        (department, name, start_date, end_date, days,
         reason, other_reason, vacation_type, note)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (department, name, start, end, days,
         reason, other_reason, vacation_type, note)
    )
    request_id = cur.fetchone()[0]
    conn.commit() # 保存を確定

    # 2. 承認用URLの作成
    # 承認者がクリックしたときにどの申請かわかるようにIDを付与します
    approve_url = f"{request.base_url}approve/{request_id}"

    # 3. Bot送信メッセージの作成
    display_reason = other_reason if reason == "その他" else reason
    message_text = (
        f"【休暇申請が届きました】\n"
        f"部署: {department}\n"
        f"氏名: {name}\n"
        f"期間: {start} ～ {end} ({days}日間)\n"
        f"種別: {vacation_type}\n"
        f"理由: {display_reason}\n\n"
        f"▼内容の確認と承認はこちら\n"
        f"{approve_url}"
    )
    
    # 【関数呼び出し】
    send_bot_message(message_text)

    return templates.TemplateResponse("complete.html", {"request": request})
    
