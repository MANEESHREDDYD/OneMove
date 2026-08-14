import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root and services/api to sys.path
root_dir = Path(__file__).parent.resolve()
services_api_dir = root_dir / "services" / "api"

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(services_api_dir) not in sys.path:
    sys.path.insert(0, str(services_api_dir))

# Load .env.local if present
env_local = root_dir / ".env.local"
if env_local.exists():
    load_dotenv(env_local)

# Set standard environment fallbacks if not present
if "SUPABASE_ANON_KEY" not in os.environ:
    os.environ["SUPABASE_ANON_KEY"] = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "mock_anon_key")

if "SUPABASE_URL" not in os.environ:
    os.environ["SUPABASE_URL"] = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321")

if "SUPABASE_SERVICE_ROLE_KEY" not in os.environ:
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock_service_role_key"

if "SUPABASE_JWT_SECRET" not in os.environ:
    os.environ["SUPABASE_JWT_SECRET"] = secrets.token_urlsafe(48)
