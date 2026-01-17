from fastapi import FastAPI
from lineworks_auth import get_access_token

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True}

@app.get("/token")
def token():
    return get_access_token()
