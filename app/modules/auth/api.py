# app/modules/auth/api.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.services import UserService
from app.core.security import create_access_token, verify_password
from app.modules.users import schemas as user_schemas

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/token")
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user_service = UserService()
    user = user_service.get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me/", response_model=user_schemas.UserResponse)
def read_users_me(current_user: user_schemas.UserResponse = Depends(get_current_user)):
    return current_user