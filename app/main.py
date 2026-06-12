from fastapi import FastAPI
from typing import Dict

app = FastAPI(
    title="Madeena Image Pipeline Scientific Execution Plane", version="0.1.0"
)


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"status": "running"}
