from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from models import User
from schemas import UserCreate, UserResponse, LoginRequest, Token
from security import get_password_hash, verify_password, create_access_token, get_current_user
from services.ledger_service import ledger_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        verification_level=user_in.verification_level or "L0",
        skills=user_in.skills or [],
        conflicts=user_in.conflicts or [],
        is_minor=user_in.is_minor or False,
        institution=user_in.institution
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=user.id,
        action="USER_REGISTERED",
        reason=f"Registered user {user.name} ({user.role})"
    )

    return user

@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
