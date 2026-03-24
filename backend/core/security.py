from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key usingFernet symmetric encryption"""
    from cryptography.fernet import Fernet
    import base64

    # Generate key from secret_key (must be 32 bytes for Fernet)
    key = base64.urlsafe_b64encode(settings.secret_key.ljust(32)[:32].encode())
    f = Fernet(key)
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """Decrypt API key"""
    from cryptography.fernet import Fernet
    import base64

    try:
        key = base64.urlsafe_b64encode(settings.secret_key.ljust(32)[:32].encode())
        f = Fernet(key)
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception:
        return None