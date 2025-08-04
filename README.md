# Microsoft OAuth Demo

Minimal Microsoft OAuth implementation with FastAPI backend and React frontend.

## Quick Start

### 1. Azure App Registration
1. Go to [Azure Portal App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Create new registration
3. Add redirect URI: `http://localhost:8003/auth/callback` (Web platform)
4. Create client secret
5. Copy Client ID and Secret

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your Microsoft OAuth credentials and Azure SSO settings
```

**Required Environment Variables:**
- `MICROSOFT_CLIENT_ID` - Your Azure app client ID
- `MICROSOFT_CLIENT_SECRET` - Your Azure app client secret
- `AZURE_TENANT_ID` - Your Azure tenant ID (or "organizations" for multi-tenant)
- `JWT_SECRET` - Secret key for JWT token signing
- `ENABLE_GROUPS_CLAIM` - Set to "true" to fetch user groups
- `ENABLE_ROLES_CLAIM` - Set to "true" to fetch user roles

### 3. Run
```bash
docker compose up --build
```

### 4. Access
- **Frontend**: http://localhost:3003
- **Backend API**: http://localhost:8003
- **API Docs**: http://localhost:8003/docs

## Features

**Backend (FastAPI)**
- Microsoft OAuth with PKCE
- Azure SSO with enterprise features
- JWT token management with refresh
- User groups and roles integration
- Protected routes
- Swagger UI

**Frontend (React + Vite)**
- Microsoft login
- User dashboard
- Token management
- Responsive design

## File Structure
```
├── backend/
│   ├── main.py          # FastAPI app with OAuth
│   ├── requirements.txt # Python dependencies
│   └── Dockerfile       # Backend container
├── frontend/
│   ├── src/
│   │   ├── App.jsx      # React app
│   │   └── main.jsx     # Entry point
│   ├── package.json     # Node dependencies
│   └── Dockerfile       # Frontend container
├── docker-compose.yml   # Container orchestration
└── .env.example         # Environment template
```

## Enterprise SSO Features

**Azure Active Directory Integration:**
- Multi-tenant support (configurable via `AZURE_TENANT_ID`)
- User groups retrieval from Azure AD
- User roles and app role assignments
- Enhanced JWT tokens with enterprise claims
- Token refresh capabilities

**Security Features:**
- PKCE (Proof Key for Code Exchange) flow
- Secure JWT token handling
- Configurable group and role claims
- Production-ready CORS configuration

**API Endpoints:**
- `GET /auth/login` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/user` - Get current user info with groups/roles
- `POST /auth/refresh` - Refresh JWT token
- `GET /health` - Health check endpoint

## Development

**Backend only**:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend only**:
```bash
cd frontend
npm install
npm run dev
```