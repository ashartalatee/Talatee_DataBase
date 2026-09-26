from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.security.dashboard_session import create_session_token, require_dashboard_session, verify_admin_credentials

router = APIRouter(prefix="/auth", tags=["dashboard-auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginBody, response: Response):
    if not verify_admin_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Username atau password salah.")
    token = create_session_token(body.username)
    response.set_cookie(
        key="talatee_session",
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=60 * 60 * 12,
    )
    return {"status": "ok"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("talatee_session")
    return {"status": "ok"}

@router.get("/me")
def me(username: str = Depends(require_dashboard_session)):
    return {"username": username}