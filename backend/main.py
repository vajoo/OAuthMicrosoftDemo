from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import httpx
import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

# Models
class LoginResponse(BaseModel):
    auth_url: str

class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str

# Determine if we're in production
is_production = os.getenv("BACKEND_URL", "").startswith("https://")
root_path = "/api" if is_production else ""

# App
app = FastAPI(
    title="Microsoft OAuth Demo",
    docs_url="/docs",
    openapi_url="/openapi.json",
    root_path=root_path
)
security = HTTPBearer()

# Get frontend URL from environment
FRONTEND_URL = os.getenv("FRONTEND_URL", f"http://{os.getenv('FRONTEND_HOST', 'localhost')}:{os.getenv('FRONTEND_PORT', '3003')}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL", f"http://{os.getenv('BACKEND_HOST', 'localhost')}:{os.getenv('BACKEND_PORT', '8003')}")
REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", f"{BACKEND_URL}/auth/callback")
AUTHORITY = "https://login.microsoftonline.com/organizations"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key")

# Storage
auth_states = {}
pkce_codes = {}

# Auth dependency
async def get_current_user(token: str = Depends(security)) -> UserInfo:
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
        return UserInfo(**payload)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
async def root():
    return {"message": "Microsoft OAuth Demo API"}

@app.get("/auth/login", response_model=LoginResponse)
async def login():
    state = secrets.token_urlsafe(32)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    auth_states[state] = {"created_at": datetime.utcnow()}
    pkce_codes[state] = code_verifier
    
    auth_url = f"{AUTHORITY}/oauth2/v2.0/authorize?" + "&".join([
        f"client_id={CLIENT_ID}",
        f"response_type=code",
        f"redirect_uri={REDIRECT_URI}",
        f"scope=openid profile email User.Read",
        f"state={state}",
        f"code_challenge={code_challenge}",
        f"code_challenge_method=S256"
    ])
    
    return {"auth_url": auth_url}

@app.get("/auth/callback")
async def callback(code: str = None, state: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {error}")
    
    if not code or not state or state not in auth_states:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    code_verifier = pkce_codes.pop(state)
    del auth_states[state]
    
    # Get access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{AUTHORITY}/oauth2/v2.0/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier
            }
        )
    
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")
    
    access_token = token_response.json()["access_token"]
    
    # Get user info
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    if user_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    user_info = user_response.json()
    
    # Create JWT
    jwt_payload = {
        "user_id": user_info["id"],
        "email": user_info.get("mail") or user_info.get("userPrincipalName"),
        "name": user_info["displayName"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    
    jwt_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")
    
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/success?token={jwt_token}")

@app.get("/auth/user", response_model=UserInfo)
async def get_user(current_user: UserInfo = Depends(get_current_user)):
    return current_user

@app.get("/health")
async def health():
    return {"status": "healthy"}