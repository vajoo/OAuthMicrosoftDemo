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
    groups: list[str] = []
    roles: list[str] = []

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = None
    expires_in: int

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

# Azure SSO Configuration
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "organizations")
AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
ENABLE_GROUPS_CLAIM = os.getenv("ENABLE_GROUPS_CLAIM", "false").lower() == "true"
ENABLE_ROLES_CLAIM = os.getenv("ENABLE_ROLES_CLAIM", "false").lower() == "true"

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key")

# Storage
auth_states = {}
pkce_codes = {}

# Auth dependency
async def get_current_user(token: str = Depends(security)) -> UserInfo:
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
        return UserInfo(
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload["name"],
            groups=payload.get("groups", []),
            roles=payload.get("roles", [])
        )
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
    
    # Enhanced scopes for Azure SSO
    scopes = ["openid", "profile", "email", "User.Read", "offline_access"]
    if ENABLE_GROUPS_CLAIM:
        scopes.append("Group.Read.All")
    if ENABLE_ROLES_CLAIM:
        scopes.append("Directory.Read.All")
    
    auth_url = f"{AUTHORITY}/oauth2/v2.0/authorize?" + "&".join([
        f"client_id={CLIENT_ID}",
        f"response_type=code",
        f"redirect_uri={REDIRECT_URI}",
        f"scope={' '.join(scopes)}",
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
    
    token_data = token_response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    
    # Get user info
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    if user_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    user_info = user_response.json()
    
    # Get user groups if enabled
    user_groups = []
    if ENABLE_GROUPS_CLAIM:
        try:
            async with httpx.AsyncClient() as client:
                groups_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/memberOf",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if groups_response.status_code == 200:
                    groups_data = groups_response.json()
                    user_groups = [group["displayName"] for group in groups_data.get("value", [])]
        except Exception as e:
            print(f"Error fetching groups: {e}")
    
    # Get user roles if enabled  
    user_roles = []
    if ENABLE_ROLES_CLAIM:
        try:
            async with httpx.AsyncClient() as client:
                roles_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/appRoleAssignments",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if roles_response.status_code == 200:
                    roles_data = roles_response.json()
                    user_roles = [role.get("principalDisplayName", "Unknown") for role in roles_data.get("value", [])]
        except Exception as e:
            print(f"Error fetching roles: {e}")
    
    # Create enhanced JWT
    jwt_payload = {
        "user_id": user_info["id"],
        "email": user_info.get("mail") or user_info.get("userPrincipalName"),
        "name": user_info["displayName"],
        "groups": user_groups,
        "roles": user_roles,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    
    # Store refresh token temporarily (in production, use secure storage)
    if refresh_token:
        jwt_payload["has_refresh"] = True
        # TODO: Store refresh_token securely (database/redis)
    
    jwt_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")
    
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/success?token={jwt_token}")

@app.get("/auth/user", response_model=UserInfo)
async def get_user(current_user: UserInfo = Depends(get_current_user)):
    return current_user

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_jwt_token(current_token: str = Depends(security)):
    """
    Refresh JWT token - extends expiration time with same user data.
    For production with Microsoft refresh tokens, implement proper OAuth refresh flow.
    """
    try:
        # Decode current token (ignore expiration for refresh)
        payload = jwt.decode(
            current_token.credentials, 
            JWT_SECRET, 
            algorithms=["HS256"],
            options={"verify_exp": False}
        )
        
        # Create new token with extended expiration
        new_payload = {
            "user_id": payload["user_id"],
            "email": payload["email"], 
            "name": payload["name"],
            "groups": payload.get("groups", []),
            "roles": payload.get("roles", []),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        new_token = jwt.encode(new_payload, JWT_SECRET, algorithm="HS256")
        
        return TokenResponse(
            access_token=new_token,
            expires_in=24 * 3600  # 24 hours in seconds
        )
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/refresh-microsoft", response_model=TokenResponse)
async def refresh_microsoft_token(request: RefreshTokenRequest):
    """
    Refresh using Microsoft refresh token - gets fresh user data from Microsoft Graph.
    Requires refresh_token to be stored securely (not implemented in this demo).
    """
    # TODO: Implement Microsoft refresh token flow
    # This would require secure storage of refresh tokens
    raise HTTPException(status_code=501, detail="Microsoft refresh token flow not implemented - use /auth/refresh for JWT refresh")

@app.get("/health")
async def health():
    return {"status": "healthy"}