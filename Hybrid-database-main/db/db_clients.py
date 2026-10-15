import os
import psycopg2
from psycopg2.extras import RealDictCursor
from neo4j import GraphDatabase
import redis
from dotenv import load_dotenv

load_dotenv()

class DatabaseClients:
    _pg_conn = None
    _neo_driver = None
    _redis_client = None

    @staticmethod
    def new_pg_connection():
        """Kết nối riêng (mỗi luồng một kết nối khi chạy song song)."""
        return psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "mental_nutrition_db"),
            user=os.getenv("POSTGRES_USER", "admin"),
            password=os.getenv("POSTGRES_PASSWORD", "password123"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )

    @classmethod
    def get_pg_connection(cls):
        if cls._pg_conn is None or cls._pg_conn.closed:
            cls._pg_conn = cls.new_pg_connection()
        return cls._pg_conn

    @classmethod
    def get_neo4j_driver(cls):
        if cls._neo_driver is None:
            cls._neo_driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
            )
        return cls._neo_driver

    @classmethod
    def get_redis_client(cls):
        if cls._redis_client is None:
            cls._redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=0,
                decode_responses=True
            )
        return cls._redis_client
