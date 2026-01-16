from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg2.extras import DictCursor
from datetime import datetime
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]

APPROVERS = {
        "mi.vida.loca.s2@gmail.com",
        "y-010.densan@af.wakwak.com"
    }

APPROVER_INFO = {
        "mi.vida.loca.s2@gmail.com": {"name" : "後藤" , "stamp" : "goto.png"},
        "y-010.densan@af.wakwak.com": {"name" : "遠藤" , "stamp" : "endo.png"}
    }

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

app = FastAPI()

@app.get("/")
def root():
    return RedirectResponse(url="/form")


# static と templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gmail API スコープ
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_lineworks_access_token():
    import os, json, time, jwt, requests

    SERVICE_ACCOUNT = os.environ["LINEWORKS_SERVICE_ACCOUNT"]
    PRIVATE_KEY_JSON = os.environ["LINEWORKS_PRIVATE_KEY"]

    private_key_info = json.loads(PRIVATE_KEY_JSON)
    PRIVATE_KEY = private_key_info["private_key"]

    now = int(time.time())

    payload = {
        "iss": SERVICE_ACCOUNT,
        "sub": SERVICE_ACCOUNT,
        "iat": now,
        "exp": now + 3600,
        "aud": "https://auth.worksmobile.com"
    }

    jwt_token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

    token_url = "https://auth.worksmobile.com/oauth2/v2.0/token"

    res = requests.post(token_url, data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
        "scope": "bot"
    })

    res.raise_for_status()
    return res.json()["access_token"]

def send_lineworks_message(user_id: str, text: str):
    import requests, os

    access_token = get_lineworks_access_token()
    bot_id = os.environ["LINEWORKS_BOT_ID"]

    url = f"https://www.worksapis.com/v1.0/bots/{bot_id}/users/{user_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "content": {
            "type": "text",
            "text": text
        }
    }

    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()


# Render 上ではローカルで生成した token.json を使う
def gmail_authenticate():
    token_path = "/etc/secrets/token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        raise Exception("token.json が見つかりません。Render 上でアップロードしてください。")
    return build('gmail', 'v1', credentials=creds)

def send_email(to, subject, body):
    service = gmail_authenticate()
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    msg = {'raw': raw}
    service.users().messages().send(userId='me', body=msg).execute()

# フォーム表示
@app.get("/form", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

# 確認画面
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
        {
            "request": request,
            "name": name,
            "department": department,
            "start": start,
            "end": end,
            "days": days,
            "reason": reason,
            "other_reason": other_reason,
            "vacation_type": vacation_type,
            "note": note
        }
    )

# 申請完了画面 + メール送信
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
    print("=== COMPLETE 開始 ===")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO leave_requests
        (department, name, start_date, end_date, days, reason, other_reason, vacation_type, note)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (department, name, start, end, days, reason, other_reason, vacation_type, note))

    request_id = cur.fetchone()[0]
    print("request_id:", request_id)

    for mail in APPROVERS:
        cur.execute("""
            INSERT INTO approvals (request_id, approver_email)
            VALUES (%s, %s)
        """, (request_id, mail))

    conn.commit()
    cur.close()
    conn.close()

    print("=== DB登録 完了 ===")

    # 🔽 ここで通知（まずはログだけ）
    print("=== LINE WORKS 通知予定 ===")

    return templates.TemplateResponse(
        "complete.html",
        {"request": request}
    )


def get_approval_status(request_id: int, email: str) -> bool:
    conn = get_db()
    cur = conn.cursor(cursor_factory=DictCursor)

    cur.execute("""
        SELECT approved
        FROM approvals
        WHERE request_id = %s
          AND approver_email = %s
    """, (request_id, email))

    row = cur.fetchone()
    cur.close()
    conn.close()

    return row and row["approved"]

def get_request_data(request_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=DictCursor)

    # ① 申請本体
    cur.execute("""
        SELECT
            department,
            name,
            start_date,
            end_date,
            days,
            reason,
            vacation_type,
            note
        FROM leave_requests
        WHERE id = %s
    """, (request_id,))

    req = cur.fetchone()
    if not req:
        cur.close()
        conn.close()
        return None

    # ② 承認一覧
    cur.execute("""
        SELECT
            approver_email,
            approved,
            approved_at
        FROM approvals
        WHERE request_id = %s
        ORDER BY id
    """, (request_id,))

    approvals = []
    for row in cur.fetchall():
        approvals.append({
            "email": row["approver_email"],            # 内部用
            "name": APPROVER_INFO[row["approver_email"]]["name"],
            "stamp": APPROVER_INFO[row["approver_email"]]["stamp"],
            "approved": row["approved"],
            "approved_at": row["approved_at"]
        })

    cur.close()
    conn.close()

    # ③ まとめて返す
    return {
        "name": req["name"],
        "department": req["department"],
        "start": req["start_date"],
        "end": req["end_date"],
        "days": req["days"],
        "reason": req["reason"],
        "vacation_type": req["vacation_type"],
        "note": req["note"],
        "approvals": approvals
    }


@app.get("/approve/{request_id}/{email}", response_class=HTMLResponse)
def approve_page(request_id: int, email: str, request: Request):
    data = get_request_data(request_id)

    approval_views = []
    for a in data["approvals"]:
        approval_views.append({
            "email": a["email"],
            "approved": a["approved"],
            "approved_at": a["approved_at"],
            "stamp": APPROVER_INFO.get(a["email"])  # ← ここ
        })

    return templates.TemplateResponse(
        "approve.html",
        {
            "request": request,
            "data": data,
            "approvals": data["approvals"],
            "email": email
        }
    )


@app.post("/approve/{request_id}/{email}")
def approve_submit(request_id: int, email: str):
    info = APPROVER_INFO.get(email)
    if not info:
        raise HTTPException(status_code=403, detail="承認権限がありません")

    stamp = info["stamp"]   # ← dict ではなく文字列

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("""
        UPDATE approvals
        SET approved = true,
            approved_at = now(),
            stamp_image = %s
        WHERE request_id = %s
          AND approver_email = %s
          AND approved = false
    """, (stamp, request_id, email))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(
    url=f"/approve/{request_id}/{email}",
    status_code=303
)