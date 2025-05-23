import logging
from pymongo import MongoClient
import motor.motor_asyncio
from info import DATABASE_URI, FALLBACK_DATABASE_URI, DATABASE_NAME, MULTI_DB_ENABLED

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MultiDBHandler:
    """Handler for supporting multiple databases."""
    
    def __init__(self):
        self.primary_uri = DATABASE_URI
        self.fallback_uri = FALLBACK_DATABASE_URI
        self.db_name = DATABASE_NAME
        self.primary_client = None
        self.fallback_client = None
        self.enabled = MULTI_DB_ENABLED
        
        # Initialize connections
        self._init_connections()
        
    def _init_connections(self):
        """Initialize database connections."""
        try:
            self.primary_client = self._get_motor_client(self.primary_uri)
            logger.info("Connected to primary database")
            
            if self.enabled and self.fallback_uri:
                self.fallback_client = self._get_motor_client(self.fallback_uri)
                logger.info("Connected to fallback database")
        except Exception as e:
            logger.error(f"Error initializing database connections: {e}")
            
    def _get_motor_client(self, uri):
        """Get a Motor client for the given URI."""
        return motor.motor_asyncio.AsyncIOMotorClient(uri)
        
    def _get_pymongo_client(self, uri):
        """Get a PyMongo client for the given URI."""
        return MongoClient(uri)
        
    async def get_collection(self, collection_name):
        """Get a collection from the primary database."""
        if not self.primary_client:
            self._init_connections()
            
        return self.primary_client[self.db_name][collection_name]
        
    async def get_fallback_collection(self, collection_name):
        """Get a collection from the fallback database."""
        if not self.enabled or not self.fallback_uri:
            return None
            
        if not self.fallback_client:
            self._init_connections()
            
        return self.fallback_client[self.db_name][collection_name]
        
    async def write_to_primary(self, collection_name, document):
        """Write a document to the primary database."""
        collection = await self.get_collection(collection_name)
        result = await collection.insert_one(document)
        return result
        
    async def write_to_fallback(self, collection_name, document):
        """Write a document to the fallback database."""
        if not self.enabled or not self.fallback_uri:
            return None
            
        collection = await self.get_fallback_collection(collection_name)
        if not collection:
            return None
            
        result = await collection.insert_one(document)
        return result
        
    async def write_to_all(self, collection_name, document):
        """Write a document to all databases."""
        primary_result = await self.write_to_primary(collection_name, document)
        fallback_result = await self.write_to_fallback(collection_name, document)
        return primary_result, fallback_result
        
    async def read_from_primary(self, collection_name, query):
        """Read a document from the primary database."""
        collection = await self.get_collection(collection_name)
        result = await collection.find_one(query)
        return result
        
    async def read_from_fallback(self, collection_name, query):
        """Read a document from the fallback database."""
        if not self.enabled or not self.fallback_uri:
            return None
            
        collection = await self.get_fallback_collection(collection_name)
        if not collection:
            return None
            
        result = await collection.find_one(query)
        return result
        
    async def read_with_fallback(self, collection_name, query):
        """Try to read from primary, fall back to secondary if not found."""
        result = await self.read_from_primary(collection_name, query)
        
        if not result and self.enabled and self.fallback_uri:
            result = await self.read_from_fallback(collection_name, query)
            
        return result
        
    async def update_primary(self, collection_name, query, update):
        """Update a document in the primary database."""
        collection = await self.get_collection(collection_name)
        result = await collection.update_one(query, update)
        return result
        
    async def update_fallback(self, collection_name, query, update):
        """Update a document in the fallback database."""
        if not self.enabled or not self.fallback_uri:
            return None
            
        collection = await self.get_fallback_collection(collection_name)
        if not collection:
            return None
            
        result = await collection.update_one(query, update)
        return result
        
    async def update_all(self, collection_name, query, update):
        """Update a document in all databases."""
        primary_result = await self.update_primary(collection_name, query, update)
        fallback_result = await self.update_fallback(collection_name, query, update)
        return primary_result, fallback_result
        
    async def delete_from_primary(self, collection_name, query):
        """Delete a document from the primary database."""
        collection = await self.get_collection(collection_name)
        result = await collection.delete_one(query)
        return result
        
    async def delete_from_fallback(self, collection_name, query):
        """Delete a document from the fallback database."""
        if not self.enabled or not self.fallback_uri:
            return None
            
        collection = await self.get_fallback_collection(collection_name)
        if not collection:
            return None
            
        result = await collection.delete_one(query)
        return result
        
    async def delete_from_all(self, collection_name, query):
        """Delete a document from all databases."""
        primary_result = await self.delete_from_primary(collection_name, query)
        fallback_result = await self.delete_from_fallback(collection_name, query)
        return primary_result, fallback_result

# Create a singleton instance
multi_db = MultiDBHandler() 