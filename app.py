from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import psycopg2

DATABASE_URL = os.environ["dpg-d5872tali9vc739svlh0-a.singapore-postgres.render.com/approval_db_bnlx"]

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
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO leave_requests
        (department, name, start_date, end_date, days, reason, other_reason, vacation_type, note)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (department, name, start, end, days, reason, other_reason, vacation_type, note))

    request_id = cur.fetchone()[0]

    approvers = [
        "mi.vida.loca.s2@gmail.com",
        "y-010.densan@af.wakwak.com"
    ]
    for mail in approvers:
        cur.execute("""
            INSERT INTO approvals (request_id, approver_email)
            VALUES (%s, %s)
        """, (request_id, mail))

    conn.commit()
    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "complete.html",
        {"request": request}
    )
