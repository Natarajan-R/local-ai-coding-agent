"""Reference: JWT authentication for FastAPI (password hashing + access/refresh tokens).

Pattern to mimic: hash passwords with passlib/bcrypt, issue a short-lived access
token and a longer refresh token with python-jose, and read the current user from a
Bearer token via an OAuth2 dependency. Adapt the field/model names to your spec.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "change-me"                       # load from config/env in real code
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; truncate to stay compatible.
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


def _create_token(data: dict, expires: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token({"sub": subject, "type": "access"},
                         timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    return _create_token({"sub": subject, "type": "refresh"},
                         timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")


def get_current_subject(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency: return the subject ('sub') from a valid access token."""
    payload = decode_token(token)
    subject = payload.get("sub")
    if not subject or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated")
    return subject
