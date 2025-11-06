"""
FCM Device Handler
"""
import uuid

from sentry_sdk.tracing import Span

from portal.libs.database import Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.models import PortalFcmDevice, PortalFcmUserDevice
from portal.serializers.v1.fcm_device import FCMCreate


class FCMDeviceHandler:
    """
    FCM Device Handler
    """

    def __init__(
        self,
        session: Session,
    ):
        self._session = session

    @distributed_trace(inject_span=True)
    async def register_device(self, device_id: str, fcm_create: FCMCreate, _span: Span = None):
        """
        Register FCM Device
        """
        try:
            await (
                self._session.insert(PortalFcmDevice)
                .values(
                    device_key=device_id,
                    token=fcm_create.fcm_token,
                    additional_data=fcm_create.additional_data,
                )
                .on_conflict_do_update(
                    index_elements=["device_key"],
                    set_={
                        "token": fcm_create.fcm_token,
                        "additional_data": fcm_create.additional_data,
                    }
                )
                .execute()
            )
        except Exception as e:
            logger.warning(f"Error registering device: {e}")
            _span.set_data("device_key", device_id)
            _span.set_data("fcm_token", fcm_create.fcm_token)
            _span.set_data("error", str(e))
            _span.set_status("error")

    @distributed_trace()
    async def bind_user_device(self, user_id: uuid.UUID, device_key: str):
        """

        :param user_id:
        :param device_key:
        :return:
        """
        try:
            device_id: uuid.UUID = await (
                self._session.select(PortalFcmDevice.id)
                .where(PortalFcmDevice.device_key == device_key)
                .fetchval()
            )
            await (
                self._session.insert(PortalFcmUserDevice)
                .values(
                    user_id=user_id,
                    device_id=device_id,
                )
                .on_conflict_do_nothing(index_elements=["user_id", "device_id"])
                .execute()
            )
        except Exception as e:
            logger.warning(f"Binding device warning: {e}")
