from fastapi import APIRouter
from pydantic import BaseModel
import jwt
from app.settings import settings

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: str

@router.get("/demo-token", response_model=TokenResponse)
def get_demo_token():
    """Returns a valid demo JWT token for the web dashboard."""
    token = jwt.encode({"sub": "sales_manager_101", "name": "Sales Manager"}, settings.jwt_secret, algorithm="HS256")
    return TokenResponse(access_token=token, user="sales_manager_101")
