from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Password Hashing: Initialize with bcrypt as recommended
# Note: user mentioned "argon2" or "bcrypt", but bcrypt is safer/standard for many envs.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    """Hash password using bcrypt."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"✘ Hashing failed: {e}")
        # User requested return False on any exception
        return False

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed one."""
    try:
        if not hashed_password:
            return False
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # User requested return False on any exception
        return False

# Pydantic Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: str

# Combined registration response including token as requested by user
class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# JWT Utilities
def create_access_token(data: dict) -> str:
    import datetime
    import jwt
    to_encode = data.copy()
    # Freshly calculated on each call to avoid stale tokens
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def get_current_user(request: Request) -> dict | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        import jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None

# Endpoints
@router.post("/register", response_model=RegisterResponse)
async def register(user_data: UserCreate, request: Request):
    from app.db.sqlitemanager import SQLiteManager
    db: SQLiteManager = request.app.state.db
    
    # 1. Check existing accounts
    if db.get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # 2. Hash password
    hashed = hash_password(user_data.password)
    if not hashed:
        raise HTTPException(status_code=500, detail="Internal hashing error")
        
    # 3. Create user (we use a specific hash creation method or standard one)
    # Using SQLiteManager.create_user (assuming it updated to accept hashed passwords or we modify it)
    # Actually, we can just modify SQLiteManager to be simpler or provide a creation method.
    user = db.create_user_with_hash(user_data.email, user_data.username, hashed)
    if not user:
        raise HTTPException(status_code=500, detail="User creation failed in database")
        
    # 4. Issue access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "username": user.username})
    
    return RegisterResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            created_at=user.created_at.isoformat(),
        )
    )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), request: Request = None):
    from app.db.sqlitemanager import SQLiteManager
    db: SQLiteManager = request.app.state.db
    
    user = db.get_user_by_email(form_data.username)
    if not user:
        user = db.get_user_by_username(form_data.username)
        
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "username": user.username})
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
async def get_me(request: Request):
    from sqlalchemy import select
    from app.db.models import User
    from app.db.sqlitemanager import SQLiteManager
    
    payload = get_current_user(request)
    if not payload:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    user_id = int(payload.get("sub"))
    db: SQLiteManager = request.app.state.db
    session = db.get_session()
    try:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            created_at=user.created_at.isoformat(),
        )
    finally:
        session.close()
