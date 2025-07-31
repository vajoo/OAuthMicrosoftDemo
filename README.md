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
# Edit .env with your Microsoft OAuth credentials
```

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
- JWT token generation
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