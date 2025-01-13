import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot settings
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
    
    # Database settings
    MONGODB_URI = os.getenv('MONGODB_URI')
    REDIS_URI = os.getenv('REDIS_URI')
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    
    # Cache settings
    CACHE_TTL = 3600  # 1 hour
    
    # Performance settings
    BATCH_SIZE = 10
    MESSAGE_QUEUE_SIZE = 1000
    PROCESS_INTERVAL = 0.1
    
    # Timeout settings
    DEFAULT_TIMEOUT = "1h"
    MAX_TIMEOUT = "24h"
    
    # Rate limiting
    MESSAGE_RATE_LIMIT = 5  # messages per second
    SEARCH_RATE_LIMIT = 1  # searches per minute