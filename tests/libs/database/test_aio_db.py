import asyncpg
import pytest

from portal.libs.database.aio_pg import PostgresConnection, ConnectionType

demo_id = '6a51312935df45bb9ad158fe7121030a'

demo_delete_id = '714a3094dbdd11e88bb99a22efe78ff5'


@pytest.mark.asyncio
async def test_fetch_demo():

    pool = await PostgresConnection()._create_pool()
    async with pool.acquire() as conn:
        values = await conn.fetch('select * from demo')
        for item in values:
            print(dict(item))


@pytest.mark.asyncio
async def test_fetch():
    pool = await PostgresConnection()._create_pool(ConnectionType.DEFAULT)
    async with pool.acquire() as conn:
        values = await conn.fetch('select * from user')
        for item in values:
            print(dict(item))


@pytest.mark.asyncio
async def test_pool_fetch():
    pool = await PostgresConnection()._create_pool(ConnectionType.DEFAULT)
    async with pool.acquire() as conn:
        values = await conn.fetch('select * from public.user')
        for item in values:
            print(dict(item))


@pytest.mark.asyncio
async def test_pool_transaction():
    pool = await PostgresConnection()._create_pool(command_timeout=600)
    async with pool.acquire() as conn:  # type:asyncpg.connection.Connection
        async with conn.transaction():  # start transaction
            status = await conn.execute('update public.demo set age=$1 where age>$2', 12, 2)
            print(status)


@pytest.mark.asyncio
async def test_fetch_demo():
    pool = await PostgresConnection()._create_pool()
    conn1 = await pool.acquire()
    conn2 = await pool.acquire()
    print(conn1)
    print(conn2)
    await pool.release(conn1)
    await pool.release(conn2)
