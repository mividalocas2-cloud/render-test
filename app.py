from fastapi import FastAPI
from lineworks_auth import load_service_account

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True}

@app.get("/debug/service-account")
def debug_service_account():
    data = load_service_account()
    return {
        "keys": list(data.keys())
    }
