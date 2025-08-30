"""
Demo API Router
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette import status
from dependency_injector.wiring import inject, Provide

from portal.container import Container
from portal.handlers import DemoHandler
from portal.serializers.mixins import GenericQueryBaseModel
from portal.serializers.v1.demo import DemoPages, DemoList
from portal.route_classes import LogRoute
from portal.libs.database import Session

router = APIRouter(
    route_class=LogRoute
)


@router.get(
    path="/pages",
    response_model=DemoPages,
    status_code=status.HTTP_200_OK
)
@inject
async def demo_pages(
    query_model: Annotated[GenericQueryBaseModel, Query()],
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> DemoPages:
    """
    Demo pages
    :param query_model:
    :param demo_handler:
    :return:
    """
    return await demo_handler.get_pages(query_model=query_model)


@router.get(
    path="/list",
    response_model=DemoList,
    status_code=status.HTTP_200_OK
)
@inject
async def demo_list(
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> DemoList:
    """
    Demo list
    :param demo_handler:
    :return:
    """
    return await demo_handler.get_list()


@router.get(
    path="/test/connection-pool",
    status_code=status.HTTP_200_OK
)
@inject
async def test_connection_pool(
    session: Session = Depends(Provide[Container.db_session])
) -> dict:
    """
    Test connection pool instance
    :param session:
    :return:
    """
    # Execute a simple query to ensure the connection is active
    await session.execute("SELECT 1")

    # Get the pool instance ID
    pool_id = id(session._pool) if session._pool else None
    conn_id = id(session._conn) if session._conn else None
    return {
        "pool_id": pool_id,
        "connection_id": conn_id,
        "is_pooled": session._use_pool,
        "is_closed": session.is_closed
    }


@router.get(
    path="/test/connection-pool/parallel",
    status_code=status.HTTP_200_OK
)
@inject
async def test_connection_pool_parallel(
    session1: Session = Depends(Provide[Container.db_session]),
    session2: Session = Depends(Provide[Container.db_session])
) -> dict:
    """
    Test connection pool with parallel requests
    :param session1:
    :param session2:
    :return:
    """

    # Execute queries on both sessions
    await session1.execute("SELECT 1")
    # Get pool and connection IDs for both sessions
    pool1_id = id(session1._pool) if session1._pool else None
    conn1_id = id(session1._conn) if session1._conn else None
    await session2.execute("SELECT 2")
    # Get pool and connection IDs for both sessions
    pool2_id = id(session2._pool) if session2._pool else None
    conn2_id = id(session2._conn) if session2._conn else None

    return {
        "session1": {
            "id": id(session1),
            "pool_id": pool1_id,
            "connection_id": conn1_id,
            "is_pooled": session1._use_pool,
            "is_closed": session1.is_closed
        },
        "session2": {
            "id": id(session2),
            "pool_id": pool2_id,
            "connection_id": conn2_id,
            "is_pooled": session2._use_pool,
            "is_closed": session2.is_closed
        },
        "same_session": session1 is session2,
        "same_pool": pool1_id == pool2_id,
        "same_connection": conn1_id == conn2_id
    }
