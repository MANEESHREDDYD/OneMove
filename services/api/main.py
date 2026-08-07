from fastapi import FastAPI
from routers import events, governance

app = FastAPI(title="ZonePilot API", version="1.5.1")

app.include_router(events.router)
app.include_router(governance.router)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/readyz")
async def readyz():
    # TODO: Verify DB readiness and collector timestamps
    return {"status": "ready"}
