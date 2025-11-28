# Backend Architecture

## Related Documentation
- [README.md](../README.md) - Documentation index
- [Project Architecture](project_architecture.md) - Overall system architecture
- [Frontend Architecture](frontend_architecture.md) - Next.js frontend

---

## 1. Overview

The backend is a FastAPI application providing REST APIs for conversation management, AI-powered project generation, and real-time chat with multiple LLM providers.

### Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Async Python web framework |
| PostgreSQL | Primary database |
| pgvector | Vector similarity search extension |
| Alembic | Database migrations |
| psycopg2 | PostgreSQL driver |
| AsyncOpenAI/AsyncAnthropic | LLM API clients |

### Key Capabilities
- Multi-provider LLM integration (OpenAI, Anthropic, Grok)
- Conversation import from ChatGPT, Claude, Grok, BranchPrompt
- Real-time streaming chat with Server-Sent Events (SSE)
- Vector-based semantic search with pgvector
- Google OAuth authentication
- S3 file storage with processing
- Linear project integration

---

## 2. Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Settings management
│   ├── routes.py            # Main router aggregator
│   ├── prompt_types.py      # Prompt type enums
│   │
│   ├── api/                 # API route handlers
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── chat_stream.py
│   │   ├── conversations.py
│   │   ├── files.py
│   │   ├── llm_defaults.py
│   │   ├── llm_prompts.py
│   │   ├── project_drafts.py
│   │   ├── projects.py
│   │   └── search.py
│   │
│   ├── middleware/
│   │   └── auth.py          # Authentication middleware
│   │
│   ├── models/              # Pydantic models
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── conversations.py
│   │   ├── llm_prompts.py
│   │   ├── project_drafts.py
│   │   └── projects.py
│   │
│   └── services/            # Business logic
│       ├── openai_service.py
│       ├── anthropic_service.py
│       ├── grok_service.py
│       ├── base_llm_service.py
│       ├── auth_service.py
│       ├── s3_service.py
│       ├── search_service.py
│       ├── search_indexer.py
│       ├── embeddings_service.py
│       ├── linear_service.py
│       ├── mem0_service.py
│       ├── summarizer_service.py
│       ├── pdf_service.py
│       ├── chunking_service.py
│       ├── database/        # Database access layer
│       │   ├── base.py
│       │   ├── users.py
│       │   ├── conversations.py
│       │   ├── chat_messages.py
│       │   ├── project_drafts.py
│       │   ├── projects.py
│       │   ├── file_attachments.py
│       │   ├── search_chunks.py
│       │   └── ...
│       └── scraper/         # Conversation parsers
│           ├── chat_gpt_parser.py
│           ├── claude_parser.py
│           ├── grok_parser.py
│           └── branchprompt_parser.py
│
├── database_migrations/     # Alembic migrations
│   ├── versions/
│   └── env.py
│
├── alembic.ini              # Alembic configuration
├── migrate.py               # Migration helper script
├── pyproject.toml           # Python dependencies
└── Dockerfile
```

---

## 3. API Routes & Endpoints

All routes prefixed with `/api`.

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/login` | Initiate Google OAuth flow |
| GET | `/callback` | OAuth callback, sets session cookie |
| GET | `/me` | Get current user info |
| GET | `/status` | Check authentication status (public) |
| POST | `/logout` | Clear session |
| DELETE | `/cleanup` | Admin: clean expired sessions |

### Conversations (`/api/conversations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/import` | Import conversation from URL (streaming) |
| GET | `/` | List all conversations (paginated) |
| GET | `/{id}` | Get conversation details |
| DELETE | `/{id}` | Delete conversation |
| PATCH | `/{id}` | Update conversation title |
| GET | `/{id}/imported_chat_summary` | Get conversation summary |
| PATCH | `/{id}/summary` | Update conversation summary |
| POST | `/import-slack` | Slack webhook import (service auth) |

### Chat (`/api/conversations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{id}/project-draft/chat` | Get chat history |
| POST | `/{id}/project-draft/chat/stream` | Stream chat with SSE |

### Files (`/api/conversations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/{id}/files` | Upload file attachment |
| GET | `/files/{file_id}/download` | Download file (signed URL) |
| GET | `/{id}/files` | List conversation files |

### Project Drafts (`/api/conversations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{id}/project-draft` | Get project draft |
| PATCH | `/{id}/project-draft` | Update title/description |
| GET | `/{id}/project-draft/versions` | Get version history |
| POST | `/{id}/project-draft/versions/{version_id}/activate` | Restore version |

### Projects (`/api/conversations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/{id}/project` | Create Linear project |
| GET | `/{id}/project` | Get Linear project info |

### LLM Configuration (`/api/llm-prompts`, `/api/llm-defaults`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/llm-prompts/{type}` | Get active prompt |
| GET | `/llm-prompts/{type}/default` | Get default prompt |
| POST | `/llm-prompts/{type}` | Create/update custom prompt |
| DELETE | `/llm-prompts/{type}` | Revert to default |
| GET | `/llm-defaults/providers` | Get available providers/models |
| GET | `/llm-defaults/{type}` | Get default LLM for prompt type |
| PUT | `/llm-defaults/{type}` | Update default LLM |

### Search (`/api/search`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Full-text + vector search |

Query params: `q`, `limit`, `offset`, `status`, `sort_by`, `sort_dir`

---

## 4. Service Layer

### LLM Services

All LLM services inherit from `BaseLLMService` providing common functionality:
- Token estimation
- Text chunking
- Map-reduce for long documents
- Document summarization

#### OpenAI Service

**Supported Models:**
| Model | Context Window | Capabilities |
|-------|---------------|--------------|
| gpt-4o | 128K | Vision, streaming |
| gpt-4o-mini | 128K | Vision, streaming |
| gpt-4-turbo | 128K | Vision, streaming |
| gpt-4.1 | 1M | Vision, PDF |
| gpt-4.1-mini | 1M | Vision, PDF |
| o1, o3, gpt-5 | Various | Advanced reasoning |

**Features:**
- Dual API support (Chat Completions + Responses API)
- Unified streaming across APIs
- Image analysis via URL

#### Anthropic (Claude) Service

**Supported Models:**
| Model | Context Window |
|-------|---------------|
| claude-opus-4 | 200K |
| claude-sonnet-4 | 200K |
| claude-3.5-haiku | 200K |
| claude-3.7-sonnet | 200K |

**Features:**
- Native streaming with content block deltas
- **Tool Calling:**
  - `update_project_draft` - AI updates project title/description
  - `create_linear_project` - Creates Linear project, locks conversation

#### Grok Service

**Supported Models:**
| Model | Context Window |
|-------|---------------|
| grok-4 | 256K |
| grok-3 | 131K |
| grok-3-mini | 131K |
| grok-code-fast-1 | 131K |

Uses OpenAI-compatible API at `https://api.x.ai/v1`

### Authentication Service

- Google OAuth 2.0 integration
- Session management (configurable expiration)
- Service key validation for service-to-service auth

### S3 Service

- File validation (magic numbers, MIME types)
- Allowed: JPEG, PNG, GIF, WebP, SVG, PDF, text
- Max size: 10MB
- Signed URL generation
- Folder structure: `conversations/{id}/files/{filename}`

### Search Services

**EmbeddingsService:**
- OpenAI `text-embedding-3-small` model
- Batch embedding support

**SearchService:**
- Multi-level matching: URL → Title → Vector
- Supports all chat platforms (ChatGPT, Claude, Grok, BranchPrompt)
- Pagination and sorting

**SearchIndexer:**
- Indexes: imported chats, draft chats, project drafts
- Configurable chunk sizes (2500-3500 chars)

### External Integrations

**LinearService:**
- GraphQL API integration
- Project creation from conversations
- Conversation locking on project creation

**Mem0Service:**
- Semantic memory search
- Score-based filtering (threshold 0.38)
- Context retrieval for project generation

**SummarizerService:**
- External metacognition API
- Background polling (5s intervals, 100min timeout)
- Supports imported and live chat summaries

---

## 5. Database Schema

### Core Tables

#### `users`
```sql
id              SERIAL PRIMARY KEY
google_id       TEXT UNIQUE NOT NULL
email           TEXT UNIQUE NOT NULL
name            TEXT NOT NULL
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

#### `user_sessions`
```sql
id              SERIAL PRIMARY KEY
user_id         FK → users
session_token   TEXT UNIQUE
expires_at      TIMESTAMPTZ
created_at      TIMESTAMPTZ
```

#### `conversations`
```sql
id              SERIAL PRIMARY KEY
url             TEXT NOT NULL
title           TEXT NOT NULL
import_date     TIMESTAMPTZ DEFAULT NOW()
imported_chat   JSONB NOT NULL          -- Array of messages
is_locked       BOOLEAN DEFAULT FALSE
imported_by_user_id  FK → users
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

#### `project_drafts`
```sql
id              SERIAL PRIMARY KEY
conversation_id FK → conversations CASCADE
active_version_id FK → project_draft_versions SET NULL
created_by_user_id FK → users
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

#### `project_draft_versions`
```sql
id              SERIAL PRIMARY KEY
project_draft_id FK → project_drafts CASCADE
title           TEXT NOT NULL
description     TEXT NOT NULL
is_manual_edit  BOOLEAN DEFAULT FALSE
version_number  INTEGER NOT NULL
created_by_user_id FK → users
created_at      TIMESTAMPTZ
```

#### `chat_messages`
```sql
id              SERIAL PRIMARY KEY
project_draft_id FK → project_drafts CASCADE
role            TEXT CHECK IN ('user', 'assistant')
content         TEXT NOT NULL
sequence_number INTEGER NOT NULL
sent_by_user_id FK → users
created_at      TIMESTAMPTZ
UNIQUE(project_draft_id, sequence_number)
```

#### `projects` (Linear)
```sql
id              SERIAL PRIMARY KEY
conversation_id FK → conversations CASCADE
linear_project_id TEXT NOT NULL
title           TEXT NOT NULL
description     TEXT NOT NULL
linear_url      TEXT NOT NULL
created_by_user_id FK → users
created_at      TIMESTAMPTZ
```

#### `file_attachments`
```sql
id              SERIAL PRIMARY KEY
chat_message_id FK → chat_messages CASCADE
conversation_id FK → conversations CASCADE
filename        TEXT NOT NULL
file_size       INTEGER NOT NULL
file_type       TEXT NOT NULL
s3_key          TEXT NOT NULL
extracted_text  TEXT
summary_text    TEXT
uploaded_by_user_id FK → users
created_at      TIMESTAMPTZ
```

#### `search_chunks` (Partitioned)
```sql
id              BIGSERIAL
source_type     TEXT NOT NULL  -- 'imported_chat', 'draft_chat', 'project_draft'
conversation_id INTEGER NOT NULL FK → conversations
chat_message_id FK → chat_messages
project_draft_id FK → project_drafts
project_draft_version_id FK → project_draft_versions
chunk_index     INTEGER NOT NULL
text            TEXT NOT NULL
embedding       vector(1536)   -- pgvector
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
PRIMARY KEY(source_type, id)
```

Partitions: `search_chunks_imported_chat`, `search_chunks_draft_chat`, `search_chunks_project_draft`

### LLM Configuration Tables

#### `llm_prompts`
```sql
id              SERIAL PRIMARY KEY
prompt_type     TEXT NOT NULL
system_prompt   TEXT NOT NULL
is_active       BOOLEAN DEFAULT TRUE
created_by_user_id FK → users
created_at      TIMESTAMPTZ
UNIQUE(prompt_type) WHERE is_active = TRUE
```

#### `default_llm_parameters`
```sql
id              SERIAL PRIMARY KEY
prompt_type     TEXT UNIQUE NOT NULL
llm_provider    TEXT NOT NULL
llm_model       TEXT NOT NULL
created_by_user_id FK → users
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

### Special Features

**PostgreSQL Extensions:**
- `pg_trgm` - Trigram fuzzy search
- `vector` (pgvector) - Vector similarity search

**Indexes:**
- Trigram: `idx_conversations_title_trgm`
- Vector: `idx_search_chunks_embedding` (IVFFLAT, cosine, lists=100)

---

## 6. Authentication

### Dual Authentication System

The middleware supports two authentication methods:

#### 1. User Authentication (Session Cookie)
```
Cookie: session_token=<token>
```
- Set by Google OAuth callback
- HTTP-only, secure cookie
- Configurable expiration (`SESSION_EXPIRE_HOURS`)

#### 2. Service Authentication (API Key)
```
Header: X-API-Key: <key>
```
- For service-to-service calls
- Hashed with SHA256 in database
- Used by Slack webhooks, external services

### OAuth Flow

```
1. GET /api/auth/login
   → Redirect to Google OAuth with state token

2. Google OAuth consent
   → Redirect to /api/auth/callback?code=...&state=...

3. GET /api/auth/callback
   → Exchange code for tokens
   → Create/update user
   → Create session
   → Set cookie
   → Redirect to frontend
```

### Public Endpoints (No Auth)

- `/`, `/health`, `/docs`, `/openapi.json`, `/redoc`
- `/api/auth/login`, `/api/auth/callback`, `/api/auth/status`

### Using Authentication in Routes

```python
from app.middleware.auth import get_current_user, require_auth

# Get current user (raises 401 if not authenticated)
user = get_current_user(request)

# Decorator for auth requirements
@require_auth(["user", "service"])
async def my_endpoint(request: Request):
    ...
```

---

## 7. Streaming & Real-time

### Server-Sent Events (SSE)

Chat streaming uses SSE for real-time responses:

```
POST /api/conversations/{id}/project-draft/chat/stream

Response: text/event-stream

Events:
- status: {"type": "status", "status": "analyzing_request"}
- content: {"type": "content", "content": "chunk of text"}
- project_updated: {"type": "project_updated", "project_draft": {...}}
- conversation_locked: {"type": "conversation_locked"}
- error: {"type": "error", "message": "..."}
- done: {"type": "done", "response": {...}}
```

### Event Types

```python
class StreamStatusEvent:
    type: "status"
    status: str  # analyzing_request, generating_response, etc.

class StreamContentEvent:
    type: "content"
    content: str

class StreamProjectUpdateEvent:
    type: "project_updated"
    project_draft: ProjectDraft

class StreamConversationLockedEvent:
    type: "conversation_locked"

class StreamErrorEvent:
    type: "error"
    message: str

class StreamDoneEvent:
    type: "done"
    response: ChatResponse
```

### Tool Calling (Claude)

Claude can autonomously call tools during chat:

```python
# Available tools:
- update_project_draft(title, description)  # Updates draft
- create_linear_project(title, description) # Creates Linear project

# Flow:
1. User sends message
2. Claude decides to use tool
3. Tool executes
4. Result sent back to Claude
5. Claude continues with result
```

---

## 8. Configuration

### Environment Variables

**Required:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
# OR individual:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ae_scientist
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# LLM APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback

# AWS S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=...
```

**Optional:**
```bash
# Server
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000

# Sessions
SESSION_EXPIRE_HOURS=24

# External Services
LINEAR_ACCESS_KEY=...
MEM0_API_URL=...
MEM0_USER_ID=...
METACOGNITION_API_URL=...
METACOGNITION_AUTH_TOKEN=...

# Frontend
FRONTEND_URL=http://localhost:3000
```

---

## 9. Development

### Running the Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt
# or
uv pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Or with specific host
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Database Migrations

```bash
cd backend

# Apply all migrations
python migrate.py upgrade

# Check current version
python migrate.py current

# View history
python migrate.py history

# Create new migration
python migrate.py revision "description of change"
```

### Adding New Endpoints

1. **Create route file** in `app/api/`:
```python
# app/api/my_feature.py
from fastapi import APIRouter, Request
from app.middleware.auth import get_current_user

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(request: Request):
    user = get_current_user(request)
    return {"message": "Hello"}
```

2. **Register router** in `app/routes.py`:
```python
from app.api.my_feature import router as my_feature_router

router.include_router(my_feature_router, prefix="/my-feature", tags=["my-feature"])
```

3. **Add Pydantic models** in `app/models/` if needed

4. **Add service logic** in `app/services/` if needed

5. **Add database operations** in `app/services/database/` if needed

### API Documentation

FastAPI auto-generates OpenAPI docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Export OpenAPI schema:
```bash
python export_openapi.py
```

### Testing

```bash
cd backend
pytest tests/
```
