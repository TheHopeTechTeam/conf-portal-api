import asyncio
import uuid
from enum import Enum
from typing import Optional

import pytest
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from app.libs.database.aio_orm import Session, _format_where
from app.libs.database.orm import ModelBase
from app.models import Demo

DEMO_ID = "6a51312935df45bb9ad158fe7121030a"
DEMO_DELETE_ID = "714a3094dbdd11e88bb99a22efe78ff5"


class A(ModelBase):
    """For demonstration"""
    __tablename__ = "a"
    __table_args__ = {"schema": "public"}
    name = sa.Column(sa.String(16))
    b_id = sa.Column(UUID, sa.ForeignKey("public.b.id"))


class B(ModelBase):
    """For demonstration"""
    __tablename__ = "b"
    __table_args__ = {"schema": "public"}
    name = sa.Column(sa.String(16))


class VMDemo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


@pytest.mark.asyncio
async def test_order():
    session = Session()
    s1 = str(session.select(Demo.id).order_by(False, lambda: Demo.age))
    s2 = str(session.select(Demo.id).order_by(True, lambda: Demo.age.desc()))
    assert s1.replace("\n", "") == "SELECT public.demo.id AS public_demo_id FROM public.demo"
    assert s2.replace("\n", "") == "SELECT public.demo.id AS public_demo_id FROM public.demo ORDER BY public.demo.age DESC"
    await session.close()


@pytest.mark.asyncio
async def test__format_statement():
    session = Session(echo=True)
    sql, params = await session._format_statement(sa.insert(Demo, dict(name="33")))
    print(sql, params)


@pytest.mark.asyncio
async def test__format_statement_string():
    session = Session(echo=True)
    sql, params = await session._format_statement("update $1,$11", None, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    print(sql, params)


@pytest.mark.asyncio
async def test_as_class():
    session = Session()
    items = await session.select(Demo) \
        .fetch(as_model=VMDemo)
    for item in items:
        print(item.name)


@pytest.mark.asyncio
async def test_as_dict():
    session = Session()
    items = await session.select(Demo).fetchdict("name", as_model=VMDemo)
    for key, value in items.items():
        print(key, value)


@pytest.mark.asyncio
async def test_update():
    class Hehe(Enum):
        Age = 1

    async with Session(echo=True, use_poll=True) as sess:
        await sess.update(Demo) \
            .values(**dict(age=Hehe.Age, birthdate="2012-01-1")) \
            .where(Demo.age > 2) \
            .execute()
        await sess.update(Demo) \
            .values(**dict(age=Hehe.Age, birthdate="2012-01-1")) \
            .where(Demo.age > 2) \
            .execute()
        await sess.update(Demo) \
            .values(**dict(age=Hehe.Age, birthdate="2012-01-1")) \
            .where(Demo.age > 2) \
            .execute()


@pytest.mark.asyncio
async def test_execute():
    async with Session() as session:
        await session.execute("update public.demo set age=22  where age>$1", 1)
        await session.execute("update public.demo set age=22  where age>$1", 1)
        await session.execute("update public.demo set age=22  where age>$1", 1)
        await session.commit()


@pytest.mark.asyncio
async def test_fetchpages():
    async with Session(echo=True) as session:
        items, count = await session.select(Demo.name) \
            .where(Demo.name.like("%57c9%")) \
            .order_by(Demo.name) \
            .offset(2) \
            .limit(4) \
            .fetchpages()
        print(items, count)

@pytest.mark.asyncio
async def test_fetchdict():
    async with Session() as session:
        data = await session.select(Demo.id) \
            .order_by(Demo.name) \
            .fetchvals("id")
        print(data)


async def worker(semaphore: asyncio.Semaphore, index: int):
    async with semaphore:
        async with Session() as session:
            did = await session.select(Demo.id) \
                .where(Demo.age > 1).fetchval()
            # await session.add(Demo, name=uuid.uuid1().hex[:16])
            await session.update(Demo) \
                .values(name=f"name {index}") \
                .where(Demo.id == did) \
                .execute()
            await asyncio.sleep(100)
            await session.commit()


@pytest.mark.asyncio
async def test_lock():
    semaphore = asyncio.Semaphore(10)
    tasks = []
    for i in range(50):
        tasks.append(worker(semaphore, i))
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_fetchrow():
    for i in range(10):
        async with Session() as session:
            values = await session.fetchrow("select * from public.demo   where age>$1", 1)
            print(values)


@pytest.mark.asyncio
async def test_outerjoin():
    async with Session() as session:
        select = session.select(A.name).outerjoin(B)
        assert str(select).replace("\n", "") == "SELECT public.a.name AS dayu_a_name FROM public.a LEFT OUTER JOIN public.b ON public.b.id = public.a.b_id"


@pytest.mark.asyncio
async def test_dynamic_join():
    async with Session() as session:
        select = session.select(A.name).dynamic_outerjoin(True, B, A.b_id == B.id)
        assert str(select).replace("\n", "") == "SELECT public.a.name AS dayu_a_name FROM public.a LEFT OUTER JOIN public.b ON public.a.b_id = public.b.id"

        select2 = session.select(A.name).dynamic_outerjoin(False, B, A.b_id == B.id)
        assert str(select2).replace("\n", "") == "SELECT public.a.name AS dayu_a_name FROM public.a"

        select3 = session.select(A.name).dynamic_join(True, B, A.b_id == B.id)
        assert str(select3).replace("\n", "") == "SELECT public.a.name AS dayu_a_name FROM public.a JOIN public.b ON public.a.b_id = public.b.id"


@pytest.mark.asyncio
async def test_on_conflict_do_nothing():
    async with Session() as session:
        stmt = session.insert(A) \
            .values(name="1") \
            .on_conflict_do_update("name",
                                   set_={"name": "foo"})
        print(stmt)


def test_format_where():
    assert str(_format_where((True, lambda: Demo.name == "foo",))) == "public.demo.name = :name_1"
    assert _format_where((None, lambda: Demo.name == "foo",)) is None
    assert _format_where((False, lambda: Demo.name == "foo",)) is None
    assert _format_where(([], lambda: Demo.name == "foo",)) is None
    assert _format_where(({}, lambda: Demo.name == "foo",)) is None
    assert str(_format_where(([1], lambda: Demo.name == "foo",))) == "public.demo.name = :name_1"
    assert str(_format_where((0, lambda: Demo.name == "foo",))) == "public.demo.name = :name_1"
    assert str(_format_where((1.1, lambda: Demo.name == "foo",))) == "public.demo.name = :name_1"


@pytest.mark.asyncio
async def test_mutil():
    session = Session()
    did = uuid.uuid1().hex
    # session.set_isolation("serializable")
    await asyncio.gather(
        create_demo_worker(session, did),
        create_demo_worker(session),
        create_demo_worker(session),
        # update_demo_worker(session, did),
    )
    await session.commit()
    await session.close()


async def create_demo_worker(session: Session, demo_id: str = None):
    if not demo_id:
        demo_id = uuid.uuid1().hex
    await session.insert(Demo) \
        .values(id=demo_id, name=uuid.uuid1().hex[:16]) \
        .execute()


async def update_demo_worker(session: Session, demo_id: str = None):
    await session.update(Demo) \
        .values(name=uuid.uuid1().hex[:16]) \
        .where(Demo.id == demo_id) \
        .execute()
