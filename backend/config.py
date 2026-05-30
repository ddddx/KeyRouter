import os
import logging
import secrets

# Server
HOST = os.getenv("KEYROUTER_HOST", "0.0.0.0")
PORT = int(os.getenv("KEYROUTER_PORT", "8000"))

# Database
DATABASE_URL = os.getenv("KEYROUTER_DATABASE_URL", "sqlite:///./keyrouter.db")

# Health check
HEALTH_CHECK_INTERVAL = int(os.getenv("KEYROUTER_HEALTH_CHECK_INTERVAL", "300"))  # seconds
HEALTH_CHECK_TIMEOUT = int(os.getenv("KEYROUTER_HEALTH_CHECK_TIMEOUT", "10"))     # seconds
HEALTH_CHECK_MAX_ERRORS = int(os.getenv("KEYROUTER_HEALTH_CHECK_MAX_ERRORS", "3"))

# Routing
MAX_RETRY_COUNT = int(os.getenv("KEYROUTER_MAX_RETRY_COUNT", "3"))
ROUTING_TIMEOUT = int(os.getenv("KEYROUTER_ROUTING_TIMEOUT", "120"))  # seconds
KEY_COOLDOWN_SECONDS = int(os.getenv("KEYROUTER_KEY_COOLDOWN_SECONDS", "900"))  # 15 minutes
MIN_KEY_COOLDOWN_SECONDS = 60

# Proxy
PROXY_URL = os.getenv("KEYROUTER_PROXY_URL", "")

# Log retention
LOG_RETENTION_DAYS = int(os.getenv("KEYROUTER_LOG_RETENTION_DAYS", "30"))  # days

# JWT Authentication
JWT_SECRET = os.getenv("KEYROUTER_JWT_SECRET", "")
JWT_EXPIRATION_HOURS = int(os.getenv("KEYROUTER_JWT_EXPIRATION_HOURS", "24"))
JWT_ALGORITHM = "HS256"

# Auto-generate JWT_SECRET if not set, persist to file
if not JWT_SECRET:
    _jwt_secret_file = os.path.join(os.path.dirname(__file__), ".jwt_secret")
    if os.path.isfile(_jwt_secret_file):
        with open(_jwt_secret_file, "r") as f:
            JWT_SECRET = f.read().strip()
    else:
        JWT_SECRET = secrets.token_urlsafe(32)
        with open(_jwt_secret_file, "w") as f:
            f.write(JWT_SECRET)
        logging.getLogger("config").info("JWT_SECRET auto-generated and saved to .jwt_secret")
