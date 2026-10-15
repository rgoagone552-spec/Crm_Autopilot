from fastapi import FastAPI
from app.api import tasks

app = FastAPI(title="CRM Autopilot")

app.include_router(tasks.router)
