from pymongo import MongoClient
import ssl
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_mongo_client(uri):
    """Create and return a MongoDB client with proper settings."""
    try:
        if uri.startswith('mongodb+srv://'):
            client = MongoClient(uri, ssl_cert_reqs=ssl.CERT_NONE)
        else:
            client = MongoClient(uri)
        return client
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise e
        
def calculate_used_storage(collection):
    """Calculate the total used storage in a collection in bytes."""
    total_size = 0
    for doc in collection.find():
        if 'file_size' in doc:
            total_size += doc.get('file_size', 0)
    return total_size 