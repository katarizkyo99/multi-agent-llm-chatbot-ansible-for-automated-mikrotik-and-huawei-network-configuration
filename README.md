# Multi-Agent LLM Chatbot for Automated MikroTik and Huawei Network Configuration

A multimodal, **multi-agent Large Language Model (LLM)-based chatbot** for automated network device configuration using **Ansible**.

This project integrates a conversational AI interface with a multi-agent LLM architecture and network automation engine to simplify the configuration of **MikroTik routers** and **Huawei switches**.

Instead of requiring users to manually construct vendor-specific command-line configurations, the system allows network administrators to submit configuration requests through a natural-language chatbot interface. The request is processed by the LLM-based orchestration layer, transformed into structured CLI instructions, and subsequently executed through an **Ansible-based automation pipeline over SSH**.

---

## System Overview

The system adopts a **multi-agent LLM architecture** in which different processing stages are separated according to their responsibilities.

The overall architecture consists of five major layers:

```text
┌─────────────────────────────────────────────────────────────┐
│                         USER LAYER                          │
│                                                             │
│              Natural Language / Image Input                │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│                                                             │
│     Next.js Chat UI        │      Topology Visualization   │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│                                                             │
│  Request Router → LLM Orchestrator → Automation Trigger    │
└───────────────┬──────────────────────┬──────────────────────┘
                │                      │
                │ Prompt + Data        │ Parsed CLI
                ▼                      ▼
┌────────────────────────┐    ┌────────────────────────────────┐
│   GENERATIVE AI ENGINE │    │ NETWORK AUTOMATION ENGINE      │
│                        │    │                                │
│   Multimodal LLM       │    │ Configuration Generator        │
│   (Groq API)           │    │ CLI → YAML Playbook            │
│                        │    │                                │
└────────────────────────┘    │ SSH Execution Engine           │
                              │ (Ansible)                      │
                              └───────────────┬────────────────┘
                                              │ SSH
                                              ▼
                              ┌────────────────────────────────┐
                              │     TARGET INFRASTRUCTURE      │
                              │                                │
                              │   MikroTik Router              │
                              │   Huawei Switch                │
                              └────────────────────────────────┘
```

---

## Architecture

### 1. Frontend Layer

The frontend is implemented using **Next.js** and provides the primary interaction interface for users.

The frontend consists of:

* Chat interface
* Text input
* Image uploader
* Topology visualization
* Chat and configuration history

User requests are transmitted to the Django backend through HTTP requests.

---

### 2. Backend Layer

The backend is implemented using **Django** and acts as the central application controller.

The backend contains three major processing components:

#### Request Router

The Request Router receives incoming requests from the frontend and determines the appropriate processing path.

Requests may contain:

* Natural-language instructions
* Configuration requests
* Images
* Chat-related data
* Network topology information

#### LLM Orchestrator

The LLM Orchestrator coordinates the interaction between the application and the generative AI engine.

Its responsibilities include:

* Processing user requests
* Forwarding prompts and relevant data to the LLM
* Interpreting LLM outputs
* Coordinating configuration-related processing
* Passing structured CLI output to the automation pipeline

#### Automation Trigger Engine

The Automation Trigger Engine determines when a configuration request should proceed to the network automation layer.

When a valid configuration request is identified, the structured CLI output is passed to the **Network Automation Engine**.

---

## 3. Multi-Agent LLM Architecture

The core intelligence of the system is based on a **multi-agent LLM architecture**.

Rather than relying on a single LLM process to perform all tasks, the system separates the processing workflow into specialized stages coordinated by the backend.

The LLM layer is implemented using a **multimodal LLM accessed through the Groq API**.

The architecture supports processing of both:

* Text-based instructions
* Image-based inputs

The general workflow is:

```text
User Input
    │
    ▼
Request Router
    │
    ▼
LLM Orchestrator
    │
    ▼
Multimodal LLM
    │
    ▼
Structured CLI
    │
    ▼
Automation Trigger
```

This separation allows the AI processing layer and the network execution layer to remain logically independent.

---

## 4. Generative AI Engine

The **Generative AI Engine** provides the LLM capabilities used by the system.

The engine communicates with the LLM through the **Groq API** and supports multimodal processing.

The main responsibilities of this component are:

* Understanding natural-language network requests
* Processing contextual information
* Processing image-based network information
* Generating structured network CLI instructions
* Providing the output required by the automation layer

The resulting output is represented as **structured CLI** before being passed to the network automation pipeline.

---

## 5. Network Automation Engine

The network configuration execution layer is implemented using **Ansible**.

Ansible serves as the automation engine responsible for converting the generated configuration instructions into executable automation tasks and sending them to the target devices.

The workflow consists of:

```text
Structured CLI
     │
     ▼
Configuration Generator
     │
     ▼
Ansible YAML Playbook
     │
     ▼
SSH Execution Engine
     │
     ▼
Target Network Device
```

### Configuration Generator

The Configuration Generator transforms the parsed CLI output into an Ansible-compatible YAML playbook.

This allows the generated configuration to be executed through an automated infrastructure workflow rather than manually entered into a device terminal.

### SSH Execution Engine

The SSH Execution Engine executes the generated Ansible configuration against the target device through SSH.

The execution result is returned to the backend and subsequently presented to the user through the frontend interface.

---

## 6. Target Network Infrastructure

The current system is designed to automate configuration for:

| Vendor   | Device |
| -------- | ------ |
| MikroTik | Router |
| Huawei   | Switch |

The architecture allows the automation layer to communicate with network devices through SSH and execute the generated configuration.

---

## 7. Database Layer

The application uses a database to persist important application data.

The database stores information related to:

* Chat sessions
* Messages
* Configuration logs
* Network device inventory
* Device aliases
* Other application state required by the chatbot

PostgreSQL is used as the primary database configuration.

---

## 8. Network Topology Visualization

The frontend provides network topology visualization functionality.

Topology information can be displayed alongside the chatbot interface to provide users with a visual representation of the network infrastructure.

The topology component is implemented using React-based visualization technologies, including:

* React Flow
* vis-network

The topology data can also be associated with individual chat sessions.

---

# Key Features

## Natural-Language Network Configuration

Users can submit network configuration requests using natural-language instructions rather than manually entering vendor-specific CLI commands.

## Multi-Agent LLM Processing

The system uses an orchestrated LLM architecture to process user requests and generate structured network configuration instructions.

## Multimodal Input

The chatbot supports both text and image-based inputs, enabling the system to process additional visual network information.

## Automated Configuration with Ansible

Generated configuration instructions are automatically transformed into Ansible playbooks and executed against target network devices.

## MikroTik and Huawei Support

The current implementation focuses on MikroTik routers and Huawei switches.

## SSH-Based Execution

Network configurations are delivered to target devices through SSH.

## Configuration History

Configuration-related activities can be persisted for later review.

## Network Topology Visualization

Users can visualize network topology through the frontend interface.

---

# End-to-End Workflow

The complete system workflow can be summarized as follows:

```text
1. User submits a text or image request
                    │
                    ▼
2. Next.js Chat Interface
                    │
                    ▼
3. Django HTTP Request Router
                    │
                    ▼
4. LLM Orchestrator
                    │
                    ▼
5. Multimodal LLM via Groq API
                    │
                    ▼
6. Structured CLI Generation
                    │
                    ▼
7. Automation Trigger Engine
                    │
                    ▼
8. Ansible Configuration Generator
                    │
                    ▼
9. YAML Playbook
                    │
                    ▼
10. SSH Execution Engine
                    │
             ┌──────┴──────┐
             ▼             ▼
        MikroTik        Huawei
         Router         Switch
             │             │
             └──────┬──────┘
                    ▼
11. Execution Result
                    │
                    ▼
12. Django Backend
                    │
                    ▼
13. Next.js Frontend
                    │
                    ▼
             User Response
```

---

# Technology Stack

## Frontend

* Next.js
* React
* React Flow
* vis-network
* Tailwind CSS

## Backend

* Python
* Django
* Django REST Framework
* django-cors-headers
* python-dotenv

## AI / LLM

* Multi-Agent LLM Architecture
* Multimodal LLM
* Groq API

## Network Automation

* Ansible
* ansible-runner
* YAML Playbooks
* SSH

## Database

* PostgreSQL
* SQLite for local development/testing

---

# Project Structure

```text
ProyekAkhir/
│
├── ansible/
│   └── Ansible playbooks and automation resources
│
├── backend/
│   ├── api/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── ...
│   │
│   ├── backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── ...
│   │
│   ├── media/
│   ├── dynamic_inventory.ini
│   ├── manage.py
│   ├── main.py
│   ├── requirements.txt
│   └── db.sqlite3
│
├── frontend/
│   ├── package.json
│   └── ...
│
├── Gambar Topologi untuk Pengujian/
│
├── Test Data Result/
│
├── package.json
├── package-lock.json
└── README.md
```

---

# Requirements

The following software is required to run the project:

* Python
* Node.js
* npm
* PostgreSQL
* Ansible
* Git

Backend dependencies are defined in:

```text
backend/requirements.txt
```

Frontend dependencies are defined in:

```text
frontend/package.json
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/katarizkyo99/ProyekAkhir.git
cd ProyekAkhir
```

## Backend

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate the environment.

### Windows

```powershell
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

---

# Environment Configuration

Create a `.env` file inside the `backend/` directory.

Example:

```env
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
```

Do not commit passwords, API keys, SSH credentials, or other secrets to GitHub.

---

# Database Setup

Run Django migrations:

```bash
cd backend
python manage.py migrate
```

Create a Django administrator account:

```bash
python manage.py createsuperuser
```

---

# Frontend Setup

```bash
cd frontend
npm install
```

---

# Running the Application

## Backend

```bash
cd backend
python main.py
```

The backend will be available at:

```text
http://localhost:8000
```

## Frontend

Open another terminal:

```bash
cd frontend
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

---

# Security Considerations

Because the application interacts directly with network infrastructure, credential security is critical.

Do not commit:

```text
.env
API keys
SSH passwords
Network device credentials
Django SECRET_KEY
Database credentials
```

For production deployment:

* Set `DEBUG=False`
* Restrict `ALLOWED_HOSTS`
* Store secrets in environment variables or a dedicated secret-management system
* Secure network device credentials
* Use HTTPS for application communication
* Restrict access to network automation services
* Follow the principle of least privilege for device accounts

---

# Development

The primary backend logic is located in:

```text
backend/api/
```

Important files include:

```text
models.py
views.py
urls.py
```

The frontend application is located in:

```text
frontend/
```

The network automation resources are located in:

```text
ansible/
```

When extending the system, maintain the separation between:

```text
Frontend
   ↓
Backend
   ↓
LLM Orchestration
   ↓
Ansible Automation
   ↓
Network Infrastructure
```

This separation is important for maintaining the scalability and reliability of the multi-agent network automation architecture.


---

# Author

**Rizky Octa Vianto**

Final Project — Internet Engineering / Network Automation

---

# Project Objective

This project aims to integrate **Large Language Models, multimodal interaction, and network automation** into a unified system for simplifying network device configuration.

By combining a **multi-agent LLM architecture** with **Ansible-based automation**, the system provides a conversational interface for network configuration while retaining an automated and structured execution layer for MikroTik routers and Huawei switches.
