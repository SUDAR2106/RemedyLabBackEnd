#remedylabs\backend\config.py
# Configuration settings for the RemedyLabs backend application
import os

# SQLite database configuration
DATABASE_FILE = "remedylab.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET","fallback_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DELTA_SECONDS = int(os.getenv("JWT_EXP_DELTA_SECONDS", 3600))