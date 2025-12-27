from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

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
    # 承認者リスト（テストユーザーのメール）
    approvers = ["mi.vida.loca.s2@gmail.com"]

    # Render 用のベース URL を設定（実際は環境変数で設定すると便利）
    base_url = "https://render-test-s1fa.onrender.com"

    body = f"""
{name} さんの休暇申請です。
所属: {department}
休暇期間: {start} 〜 {end} ({days}日間)
種類: {vacation_type}
理由: {reason} {other_reason}
備考: {note}
承認リンク: {base_url}/approve
"""
    for a in approvers:
        send_email(a, f"{name} さんの休暇申請", body)

    return templates.TemplateResponse("complete.html", {"request": request})
