# ProyekAkhir

ProyekAkhir is a web application combining a Django REST backend and a React/Next.js frontend for working with network topology data, chat-like interactions, and device configuration history. The backend stores chats, messages, network devices and configuration history; the frontend contains a topology/visualization UI (React + Next.js + React Flow / vis-network).

## Features

- Chat-like data model for storing conversations and topology JSON per chat.
- Messages can include text and images (uploaded to media/chat_images).
- Persistence of configuration history (RiwayatKonfigurasi) with optional images.
- Network device inventory model (NetworkDevice + DeviceAlias) for storing credentials and vendor info.
- Backend implemented with Django + Django REST Framework.
- Frontend implemented with Next.js and React (uses React Flow and vis-network for topology visualization).
- Some repo files indicate integration points with Ansible (ansible-runner dependency and dynamic_inventory.ini present), suggesting automation workflows are intended.

## System Architecture

- Frontend (frontend/): Next.js app that renders UI and topology visualizations. It communicates with the backend over HTTP (API endpoints implemented in backend/api/).
- Backend (backend/): Django project exposing REST endpoints (Django REST Framework). Models represent Chat, Message, RiwayatKonfigurasi, NetworkDevice, DeviceAlias.
- Database: Backend is configured to use PostgreSQL through environment variables, but the repository contains a db.sqlite3 file (see Notes / Ambiguities).
- Optional automation: ansible-runner and a dynamic_inventory.ini file indicate Ansible-based automation is (or was) intended to execute network configuration tasks.

## Tech Stack

- Frontend
  - Next.js (React)
  - React 19
  - React Flow (reactflow)
  - vis-network
  - Tailwind CSS
- Backend
  - Python, Django 5.x
  - Django REST Framework
  - django-cors-headers
  - python-dotenv
  - ansible-runner
- Database
  - Configured for PostgreSQL (psycopg2-binary). A SQLite file (backend/db.sqlite3) exists in the repo (used likely for local testing).
- Dev / Tools
  - Node.js (frontend)
  - npm / package-lock.json

## Project structure (top-level / important files)

text representation:
ProyekAkhir/
├── Gambar Topologi untuk Pengujian/    (topology images for testing)
├── Test Data Result/                   (test output)
├── ansible/                            (Ansible playbooks/inventory — review)
├── backend/                            (Django project & API)
│   ├── .env                            (environment file — DO NOT commit secrets)
│   ├── main.py                         (runs Django dev server)
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3                      (local DB file)
│   ├── dynamic_inventory.ini
│   ├── api/                            (Django app: models, views, urls)
│   ├── media/                          (uploads)
│   └── backend/                        (Django project settings, urls)
├── frontend/                           (Next.js app)
│   └── package.json
├── package.json                        (root; contains small dependency list)
├── package-lock.json
├── node_modules/
└── postgres-data/                      (data directory, likely for local Postgres)

Notes on important backend files:
- backend/backend/settings.py — Django settings. DEBUG = True, SECRET_KEY present in file (needs removal), database configured via env vars for PostgreSQL by default.
- backend/api/models.py — defines Chat, Message, RiwayatKonfigurasi, NetworkDevice, DeviceAlias (see Database section below).
- backend/api/views.py & backend/api/urls.py — REST endpoints implementation (inspect these files to document exact endpoints).

## Requirements

Confirmed files indicate the following requirements:
- Python (3.10+ recommended for Django 5.x; check local environment)
- Node.js (for frontend; Next.js 16 suggests Node 18+)
- PostgreSQL (recommended for production; backend settings default to PostgreSQL via env variables)
- For quick local testing: repository includes a SQLite DB (backend/db.sqlite3) but settings use Postgres — see Ambiguities.
- Python packages (backend/requirements.txt):
  - Django
  - djangorestframework
  - requests
  - python-dotenv
  - django-cors-headers
  - psycopg2-binary
  - ansible-runner
- npm packages (frontend/package.json, root package.json)

## Installation

1. Backend (local dev)
   - Create and activate Python virtual environment:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - Install dependencies:
     - pip install -r backend/requirements.txt
   - Environment: create backend/.env (do not commit secrets). Settings read env vars:
     - DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
   - If you intend to use the included SQLite DB file (for quick testing), be aware settings.py are set for PostgreSQL. Confirm whether to adjust DATABASES or provide Postgres credentials.

2. Frontend
   - cd frontend
   - npm install
   - npm run dev (starts Next.js dev server)

## Configuration

- backend/.env (exists in repo) — review and remove any committed secrets. Use .env to set:
  - DB_NAME
  - DB_USER
  - DB_PASSWORD
  - DB_HOST
  - DB_PORT
  - (any other environment variables you prefer)
- backend/backend/settings.py currently contains:
  - SECRET_KEY hard-coded (replace with environment variable)
  - DEBUG = True (set to False in production)
  - ALLOWED_HOSTS = ['*'] (tighten in production)

Do not commit credentials or secret keys. Use environment variables for production configuration.

## Running the project

Backend (development)
- From repository root:
  - cd backend
  - python main.py
  - This file runs: manage.py runserver 0.0.0.0:8000

Typical Django commands:
- python manage.py migrate
- python manage.py createsuperuser
- python manage.py runserver

Frontend (development)
- cd frontend
- npm run dev
- By default Next.js runs on http://localhost:3000 — configure API base URLs in the frontend where applicable so requests go to the Django API (e.g., http://localhost:8000).

Notes:
- The backend settings expect PostgreSQL via env vars. If you want to use the included SQLite DB, verify settings and modify DATABASES accordingly (or run migrations to create a new SQLite DB if you change settings).

## API Documentation (high-level)

The backend app `api` contains models and REST views. The code shows these primary resources (models are source-of-truth):

Models (backend/api/models.py)
- Chat
  - id: UUID
  - title: string
  - topology_data: JSONField (stores topology/graph data)
  - created_at: timestamp
- Message
  - id: UUID
  - chat: FK -> Chat (related_name="messages")
  - role: string
  - content: text
  - image: ImageField (chat_images/)
  - timestamp: timestamp
- RiwayatKonfigurasi (configuration history)
  - config: text
  - status: text
  - image: ImageField (riwayat_images/)
  - created_at: timestamp
- NetworkDevice
  - name, host, port, username, password, vendor
- DeviceAlias
  - alias_name -> FK to NetworkDevice

Where to find endpoints:
- Implementation lives in backend/api/views.py and routes are registered in backend/api/urls.py and backend/backend/urls.py. Inspect these files to produce exact Method/Path tables.

Recommendation: add a concise API table in docs (or enable DRF browsable API / Swagger / Redoc) that lists exact endpoints, HTTP methods, request/response fields and authentication (if any).

## Database

- The repository includes backend/db.sqlite3 (local DB file).
- settings.py is configured to use PostgreSQL by default (psycopg2-binary).
- Primary tables derived from models.py:
  - tabel_chat
  - tabel_pesan
  - riwayat_konfigurasi
  - plus tables for NetworkDevice and DeviceAlias

## Ansible / Automation

- ansible-runner is listed in backend/requirements.txt and the repo includes dynamic_inventory.ini in backend/. This suggests the backend might run Ansible playbooks (via ansible-runner) to execute configuration tasks on network devices stored in NetworkDevice.
- The exact orchestration (which views call ansible-runner, playbook locations, or inventory generation) must be inspected in backend/api/views.py.

## Troubleshooting (observed issues & quick fixes)

- SECRET_KEY is committed in settings.py — rotate/remove immediately and load via environment variable.
- DEBUG = True and ALLOWED_HOSTS = ['*'] — not safe for production.
- Mixed DB artifacts: repository contains db.sqlite3 while settings are set for PostgreSQL. Confirm which DB is intended for production and update docs.
- node_modules is committed — it's recommended to remove node_modules from the repo and add it to .gitignore; use package-lock.json / package.json to reproduce.
- backend/.env is present in repo — ensure it contains no sensitive data. If it does, remove and rotate secrets.

## Security notes

- Remove SECRET_KEY from version control and load it from environment variables.
- Do not commit .env or any file containing real credentials (NetworkDevice password fields may expose secrets elsewhere; check carefully).
- Tighten DEBUG and ALLOWED_HOSTS for production.
- NetworkDevice model stores plaintext passwords — consider secret management, encryption, or avoiding storing credentials in DB.

## Development

- To add features, inspect backend/api/views.py (large file) to find endpoints and how requests are handled.
- Consider splitting views file into smaller modules (by resource) and add proper API documentation (OpenAPI / Swagger).
- Add tests for critical endpoints. backend/api/tests.py currently exists but is minimal.

## Contributing

- No CONTRIBUTING.md found. Suggested minimal rules:
  - Fork → branch → open PR to main.
  - Run backend tests and frontend lint/build before submitting.
  - Keep secrets out of commits.

## License

- No license file detected in the repository. If you intend to open-source, add a LICENSE file (MIT/Apache/GPL etc.) as appropriate.

## Author

Repository owner: katarizkyo99 (no additional author metadata found inside repo).
