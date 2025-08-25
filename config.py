import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for the bot"""
    
    # Required API tokens
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
    
    # Optional configurations with defaults
    CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))  # Max messages per chat
    RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "10"))  # Seconds between commands
    
    # Authorized users (comma-separated list of Telegram user IDs)
    AUTHORIZED_USERS = [int(x.strip()) for x in os.getenv("AUTHORIZED_USERS", "").split(",") if x.strip()]
    
    # Logging level
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        required_vars = [
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
