# This module will handle configuration and environment variables.
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- Core Bot Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

# --- AI Provider Configuration ---
# Defaults to 'openai' if not set
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()

# API Keys for different providers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
