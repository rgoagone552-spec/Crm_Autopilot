import os
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from app.api import tasks, contacts, deals, autopilot, auth
from app.dependencies.auth import get_current_user

app = FastAPI(title="CRM Autopilot")

@app.get("/health")
async def health():
    return {"status": "ok"}

# Public Auth router
app.include_router(auth.router, prefix="/auth")

# Protected API Routers
app.include_router(tasks.router, prefix="/tasks", dependencies=[Depends(get_current_user)])
app.include_router(contacts.router, prefix="/contacts", dependencies=[Depends(get_current_user)])
app.include_router(deals.router, prefix="/deals", dependencies=[Depends(get_current_user)])
app.include_router(autopilot.router, prefix="/autopilot", dependencies=[Depends(get_current_user)])

# Mount static frontend dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
