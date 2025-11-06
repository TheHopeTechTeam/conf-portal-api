"""
FCM Device API
"""
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Request, Response
from starlette import status

from portal.container import Container
from portal.handlers import FCMDeviceHandler
from portal.route_classes import LogRoute
from portal.serializers.v1.fcm_device import FCMCreate

router = APIRouter(
    route_class=LogRoute
)


@router.post(
    path="/register/{device_id}",
    status_code=status.HTTP_201_CREATED,
)
@inject
async def register_device(
    request: Request,
    response: Response,
    device_id: str,
    fcm_create: FCMCreate,
    fcm_device_handler: FCMDeviceHandler = Depends(Provide[Container.fcm_device_handler]),
):
    """

    :param request:
    :param response:
    :param device_id:
    :param fcm_create:
    :param fcm_device_handler:
    :return:
    """
    await fcm_device_handler.register_device(device_id, fcm_create)
