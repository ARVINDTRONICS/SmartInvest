# SmartInvest AI - Enterprise Smart SIP Investment Platform

SmartInvest AI is an enterprise-grade, AI-powered Smart SIP (Systematic Investment Plan) Investment Platform designed to optimize the execution day of monthly SIP investments within a strict calendar window. 

The platform supports:
*   **Indian Mutual Funds** (via Zerodha Kite Connect)
*   **US ETFs** (via Interactive Brokers API)

## 📌 Core Investment Philosophy
*   **Never skip a SIP**: Continuous market participation is guaranteed.
*   **No market timing/prediction**: The platform does not predict future prices or attempt to time macro cycles.
*   **Window Optimization**: It attempts to buy during short-term corrections/oversold levels *only inside* a configurable monthly window (e.g., 10 days).
*   **Deterministic Fallback**: If no specific signals trigger by the final day of the investment window, the SIP automatically executes on that day.
*   **Explainable Decisions**: Every recommendation is backed by a deterministic score matrix and translated into clear explanations by LangGraph AI agents.

---

## 🛠️ Technology Stack
*   **Backend**: Python 3.13, FastAPI, SQLAlchemy, Pydantic v2
*   **Database & Cache**: PostgreSQL (16), Redis (7)
*   **AI Engine**: LangGraph, LangChain, OpenAI GPT models
*   **Scheduler**: APScheduler (running daily collection at 18:30 IST / 13:00 UTC)
*   **Proxy & Web**: Nginx (alpine)
*   **Containers**: Docker, Docker Compose

---

## 📂 Repository Structure
```text
smart-invest/
├── .github/workflows/       # GitHub Actions CI pipelines
├── ai/                      # LangGraph workflows and nodes
│   └── graph/
├── app/                     # FastAPI core application logic
│   ├── api/                 # Endpoints (health, market, decision)
│   ├── config/              # BaseSettings configuration
│   └── core/                # Database, Redis, and Logging setups
├── collectors/              # Data collection scraping modules (yfinance, rss)
├── database/                # Database models and table definitions
├── decision_engine/         # Deterministic scoring matrix and rule engine
├── indicators/              # Mathematics calculations engine (RSI, MACD, SMA)
├── nginx.conf               # Nginx reverse proxy configuration
├── Dockerfile               # Multi-stage secure virtualenv Docker build
├── docker-compose.yml       # Docker container stack orchestration
└── requirements.txt         # Core dependencies list
```

---

## ⚙️ Environment Configuration

Create a `.env` file at the root of the project to configure the environment variables:

```ini
# System Configuration
ENVIRONMENT=production   # Options: development, production, testing
LOG_LEVEL=INFO           # Options: DEBUG, INFO, WARNING, ERROR

# Database URLs
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/smartinvest
REDIS_URL=redis://redis:6379/0

# LangGraph AI Configuration
OPENAI_API_KEY=sk-proj-...   # Required for AI explanations

# Telegram Bot Notifications
TELEGRAM_BOT_TOKEN=1234567890:ABC... # From BotFather
TELEGRAM_CHAT_ID=-100123456789       # Your Chat/Channel ID
```

---

## 🚀 Deployment & Hosting Options

### 1. Local Development / Sandbox Testing
You can run and test the complete stack locally using **Docker Compose**.

```bash
# 1. Clone and navigate to repository
git clone https://github.com/ARVINDTRONICS/SmartInvest.git
cd SmartInvest

# 2. Configure environment keys
cp .env.example .env   # Or create your own .env

# 3. Build and launch all containers
docker compose up --build -d

# 4. Check running status
docker compose ps
```

*Access the interactive API documentation (Swagger) at: `http://localhost/docs`*

---

### 2. Production: Hetzner Cloud VPS (Recommended)
Deploying to a Hetzner Cloud VPS (Ubuntu 22.04 LTS or 24.04 LTS) is recommended.

#### A. Install Docker and Docker Compose on VPS
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl gitufw

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Enable Firewall (allow only HTTP, HTTPS, and SSH)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### B. Setup the Codebase
Clone the code to your VPS `/var/www/smartinvest` folder, configure production database passwords in `.env`, and boot up:
```bash
mkdir -p /var/www
git clone https://github.com/ARVINDTRONICS/SmartInvest.git /var/www/smartinvest
cd /var/www/smartinvest

# Setup production environment variables
nano .env

# Build and start services
docker compose up --build -d
```

#### C. SSL Configuration (Let's Encrypt HTTPS)
To secure endpoint communications with SSL/TLS, run `certbot` on your host machine to get SSL certificates and mount them into Nginx:

1.  Modify `nginx.conf` on your host to listen on port 443 with SSL certificate paths.
2.  Install Certbot on the host VPS:
    ```bash
    sudo apt install -y certbot python3-certbot-nginx
    sudo certbot --nginx -d yourdomain.com
    ```

---

## 📡 REST API References

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Live system dependency status checks (DB, Redis) | `200 OK` |
| `GET` | `/market/today` | Fetch latest cached market prices and FII/DII flows | `200 OK` |
| `POST` | `/market/collect` | Asynchronously seeding market prices/indicators (bg task) | `202 Accepted` |
| `POST` | `/news/collect` | Asynchronously crawling historical financial news (bg task) | `202 Accepted` |
| `GET` | `/decision` | Evaluate optimal day recommendation for target symbol | `200 OK` |

#### Triggering Seeding manually
```bash
# Seed 180 days of prices/indicators
curl -X POST "http://localhost/market/collect?days=180"

# Seed 30 days of financial news RSS feeds
curl -X POST "http://localhost/news/collect?days=30"
```

---

## 🧪 Verification & Testing
To run the full Pytest unit test suite inside your local virtual environment:

```bash
# Set PYTHONPATH and execute pytest
PYTHONPATH=. .venv/bin/pytest tests/
```
All 19 tests will run, testing yfinance base scrapers, technical indicators math, score rules, LangGraph compilation, and Telegram notification dispatchers.
