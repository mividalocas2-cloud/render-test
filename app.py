# ==============================
# standard library
# ==============================
import os
import json
import time
from datetime import datetime

# ==============================
# third party
# ==============================
import psycopg2
from psycopg2.extras import DictCursor
import jwt
import requests

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# ==============================
# environment
# ==============================
DATABASE_URL = os.environ["DATABASE_URL"]
LINEWORKS_SERVICE_ACCOUNT = os.environ["LINEWORKS_SERVICE_ACCOUNT"]
LINEWORKS_PRIVATE_KEY = os.environ["LINEWORKS_PRIVATE_KEY"]
LINEWORKS_BOT_ID = os.environ["LINEWORKS_BOT_ID"]


# ==============================
# constants
# ==============================
APPROVERS = {
    "mi.vida.loca.s2@gmail.com",
    "y-010.densan@af.wakwak.com"
}

APPROVER_INFO = {
    "mi.vida.loca.s2@gmail.com": {"name": "後藤", "stamp": "goto.png"},
    "y-010.densan@af.wakwak.com": {"name": "遠藤", "stamp": "endo.png"}
}


# ==============================
# database
# ==============================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ==============================
# LINE WORKS
# ==============================
def get_lineworks_access_token() -> str:
    private_key_info = json.loads(LINEWORKS_PRIVATE_KEY)
    private_key = private_key_info["private_key"]

    now = int(time.time())

    payload = {
        "iss": LINEWORKS_SERVICE_ACCOUNT,
        "sub": LINEWORKS_SERVICE_ACCOUNT,
        "iat": now,
        "exp": now + 3600,
        "aud": "https://auth.worksmobile.com"
    }

    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

    res = requests.post(
        "https://auth.worksmobile.com/oauth2/v2.0/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt_token,
            "scope": "bot"
        }
    )

    res.raise_for_status()
    return res.json()["access_token"]


def send_lineworks_message(user_id: str, text: str) -> None:
    access_token = get_lineworks_access_token()

    url = (
        f"https://www.worksapis.com/v1.0/bots/"
        f"{LINEWORKS_BOT_ID}/users/{user_id}/messages"
    )

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


# ==============================
# FastAPI
# ==============================
app = FastAPI()


@app.get("/")
def root():
    return RedirectResponse(url="/form")


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ==============================
# routes
# ==============================
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

    for mail in APPROVERS:
        cur.execute(
            """
            INSERT INTO approvals (request_id, approver_email)
            VALUES (%s, %s)
            """,
            (request_id, mail)
        )

    conn.commit()
    cur.close()
    conn.close()

    # LINE WORKS 通知
    send_lineworks_message(
        user_id="あなたのユーザーid",
        text=f"""
【休暇申請】
申請者：{name}
期間：{start} ～ {end}（{days}日）

承認はこちら
https://あなたのURL/approve/{request_id}/承認者メール
"""
    )

    return templates.TemplateResponse(
        "complete.html",
        {"request": request}
    )


@app.get("/approve/{request_id}/{email}", response_class=HTMLResponse)
def approve_page(request_id: int, email: str, request: Request):
    data = get_request_data(request_id)
    return templates.TemplateResponse(
        "approve.html",
        {"request": request, "data": data, "email": email}
    )


@app.post("/approve/{request_id}/{email}")
def approve_submit(request_id: int, email: str):
    info = APPROVER_INFO.get(email)
    if not info:
        raise HTTPException(status_code=403, detail="承認権限がありません")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE approvals
        SET approved = true,
            approved_at = now(),
            stamp_image = %s
        WHERE request_id = %s
          AND approver_email = %s
          AND approved = false
        """,
        (info["stamp"], request_id, email)
    )

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(
        url=f"/approve/{request_id}/{email}",
        status_code=303
    )


# ==============================
# helpers
# ==============================
def get_request_data(request_id: int):
    conn = get_db()
    cur = conn.cursor(cursor_factory=DictCursor)

    cur.execute(
        """
        SELECT department, name, start_date, end_date,
               days, reason, vacation_type, note
        FROM leave_requests
        WHERE id = %s
        """,
        (request_id,)
    )
    req = cur.fetchone()
    if not req:
        return None

    cur.execute(
        """
        SELECT approver_email, approved, approved_at
        FROM approvals
        WHERE request_id = %s
        ORDER BY id
        """,
        (request_id,)
    )

    approvals = []
    for row in cur.fetchall():
        info = APPROVER_INFO[row["approver_email"]]
        approvals.append({
            "email": row["approver_email"],
            "name": info["name"],
            "stamp": info["stamp"],
            "approved": row["approved"],
            "approved_at": row["approved_at"]
        })

    cur.close()
    conn.close()

    return {
        "department": req["department"],
        "name": req["name"],
        "start": req["start_date"],
        "end": req["end_date"],
        "days": req["days"],
        "reason": req["reason"],
        "vacation_type": req["vacation_type"],
        "note": req["note"],
        "approvals": approvals
    }
