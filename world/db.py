# db.py
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os

load_dotenv()

class Database:
    _connection_pool = None
    
    @classmethod
    def initialize(cls):
        cls._connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
    
    @classmethod
    def get_connection(cls):
        conn = cls._connection_pool.getconn()
        
        # Register vector for this connection
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(conn)
        except ImportError:
            print("pgvector not available, vector operations will be limited")
        
        # Register UUID for this connection
        from psycopg2.extras import register_uuid
        register_uuid(conn)
        
        return conn
    
    @classmethod
    def return_connection(cls, connection):
        cls._connection_pool.putconn(connection)
    
    @classmethod
    def close_all(cls):
        cls._connection_pool.closeall()

# Initialize on import
Database.initialize()