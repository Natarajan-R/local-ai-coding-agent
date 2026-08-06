"""Reference: a FastAPI router with dependencies and Pydantic request/response models.

Pattern to mimic: define an APIRouter (with prefix/tags), validate input with Pydantic
models, inject the session and current user with Depends(), type responses with
response_model, and raise HTTPException with the right status codes. Adapt names to
your spec. (Uses plain `str` for email to avoid the optional email-validator dep.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str


async def get_session():
    """Placeholder dependency — mirror your real session provider here."""
    ...


async def get_current_user(session=Depends(get_session)):
    """Placeholder dependency — resolve the authenticated user here."""
    ...


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session=Depends(get_session)):
    # Call your service to persist; translate domain errors to HTTP status codes.
    if payload.email == "taken@example.com":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    return UserOut(id=1, email=payload.email)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, session=Depends(get_session)):
    if user_id != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut(id=user_id, email="user@example.com")


@router.get("/me", response_model=UserOut)
async def read_me(current=Depends(get_current_user)):
    return current
