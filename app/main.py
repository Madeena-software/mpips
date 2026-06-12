from fastapi import FastAPI, Depends
from typing import Dict, Any
from app.core.security import verify_token
from app.api.v1.router import router as api_v1_router

app = FastAPI(
    title="Madeena Image Pipeline Scientific Execution Plane", version="0.1.0"
)

app.include_router(api_v1_router)


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"status": "running"}


@app.get("/v1/secure-test")
def secure_test(payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    return {
        "message": "Authentication successful",
        "client_id": payload.get("sub"),
        "scopes": payload.get("scope"),
        "tenant_id": payload.get("tenant_id"),
    }
