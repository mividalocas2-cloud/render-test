from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.post("/confirm", response_class=HTMLResponse)
def confirm(
    request: Request,
    department: str = Form(...),
    name: str = Form(...),
    start: str = Form(...),
    end: str = Form(...),
    days: str = Form(...),
    reason: str = Form(...),
    other_reason: str = Form("")
):
    return templates.TemplateResponse(
        "confirm.html",
        {
            "request": request,
            "department": department,
            "name": name,
            "start": start,
            "end": end,
            "days": days,
            "reason": other_reason if reason == "other" else reason,
        }
    )


@app.post("/complete", response_class=HTMLResponse)
def complete(request: Request):
    return templates.TemplateResponse("complete.html", {"request": request})
