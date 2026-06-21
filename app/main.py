"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="PPT Maker", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
