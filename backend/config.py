import os

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

# Proxy
PROXY_URL = os.getenv("KEYROUTER_PROXY_URL", "")