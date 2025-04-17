import logging
import os
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConnectionFailure, ConfigurationError, ServerSelectionTimeoutError
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def verify_mongodb_uri():
    """Verify that the MongoDB URI is properly configured"""
    uri = os.getenv('MONGODB_URI')
    if not uri:
        raise ConfigurationError("MONGODB_URI not found in environment variables")
    if not uri.startswith('mongodb+srv://'):
        raise ConfigurationError("Invalid MongoDB URI format. Must start with mongodb+srv://")
    return uri

def get_database():
    try:
        uri = verify_mongodb_uri()
        
        # MongoClient with explicit TLS settings
        client = MongoClient(
            uri,
            maxPoolSize=50,
            minPoolSize=10,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
            retryWrites=True,
            w='majority',
            serverSelectionTimeoutMS=10000,
            heartbeatFrequencyMS=10000,
            tls=True,
            tlsAllowInvalidCertificates=False  # Set to True ONLY if testing with self-signed certs
        )

        # Test the connection
        logger.info("Pinging MongoDB server...")
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB Atlas!")

        db = client['webx_microscope']
        db.command('ping')
        logger.info("Successfully accessed database!")
        
        return db

    except ServerSelectionTimeoutError as e:
        logger.error(f"Server selection timeout. MongoDB not reachable: {e}")
        raise
    except ConnectionFailure as e:
        logger.error(f"Could not connect to MongoDB Atlas: {e}")
        raise
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        raise

def execute_with_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except AutoReconnect:
            if attempt == max_retries - 1:
                logger.error(f"Operation failed after {max_retries} retries")
                raise
            logger.warning(f"Connection lost, retrying... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(0.5 * (attempt + 1))
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

def log_database_operation(operation, success, error=None):
    if success:
        logger.info(f"Database operation '{operation}' completed successfully")
    else:
        logger.error(f"Database operation '{operation}' failed: {error}")

# Initialize database connection
try:
    db = get_database()

    try:
        db.users.create_index('email', unique=True)
        db.bookings.create_index([('microscope_id', 1), ('date', 1), ('start_time', 1)])
        db.bookings.create_index('user_id')
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise

except Exception as e:
    logger.error(f"Failed to initialize database connection: {e}")
    raise
