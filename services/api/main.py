from fastapi import FastAPI
from services.api.routers import events, governance, observatory, health

app = FastAPI(title="ZonePilot API", version="1.5.1")

app.include_router(events.router)
app.include_router(governance.router)
app.include_router(observatory.router)
app.include_router(health.router)

@app.get("/readyz")
async def readyz():
    # TODO: Verify DB readiness and collector timestamps
    return {"status": "ready"}
