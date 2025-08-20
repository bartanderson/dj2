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
        return cls._connection_pool.getconn()
    
    @classmethod
    def return_connection(cls, connection):
        cls._connection_pool.putconn(connection)
    
    @classmethod
    def close_all(cls):
        cls._connection_pool.closeall()

# Initialize on import
Database.initialize()