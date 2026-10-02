import os
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="STRATOS API", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "STRATOS API is running"}
