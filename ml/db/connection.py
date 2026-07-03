import os
from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()
_pool = None
async def init_pool():
    global _pool

    conn_str = (
        f"host={os.getenv('DB_HOST')} "
        f"port={os.getenv('DB_PORT', 5432)} "
        f"dbname={os.getenv('DB_NAME')} "
        f"user={os.getenv('DB_USER')}"
    )
    
    password = os.getenv('DB_PASSWORD')
    if password:
        conn_str += f" password={password}"
        
    try:
        _pool = AsyncConnectionPool(
            conninfo=conn_str,
            min_size=2,
            max_size=5,
            kwargs={"autocommit": True},
            open=False
        )
        await _pool.open()
        await _pool.wait()
        print("[ml-db] Async connection pool initialized.", flush=True)
    except Exception as e:
        print(f"[ml-db] Pool initialization failed: {e}", flush=True)
        raise

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        print("[ml-db] Connection pool closed.", flush=True)
@asynccontextmanager

async def get_connection():

    if _pool is None:
        raise RuntimeError("Pool not initialised. Call await init_pool() first.")
    async with _pool.connection() as conn:
        await conn.set_read_only(True) 
        yield conn