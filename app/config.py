# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # load file .env

MONGO_DETAILS = os.getenv("MONGO_DETAILS")
DATABASE_NAME = os.getenv("DATABASE_NAME")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
