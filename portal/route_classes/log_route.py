"""
LogRouting
"""
import time
from typing import Callable, Dict, Any

from fastapi import Request, Response
from fastapi.routing import APIRoute

from portal.config import settings
from portal.libs.logger import logger


class LogRoute(APIRoute):
    """LogRouting"""

    @staticmethod
    def filter_sensitive_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter sensitive parameters from query params to prevent logging sensitive information.

        :param params: Dictionary of query parameters
        :return: Dictionary with sensitive values replaced by "***"
        """
        filtered_params = {}
        for key, value in params.items():
            # Check if the parameter name (case-insensitive) contains sensitive keywords
            key_lower = key.lower()
            is_sensitive = any(
                sensitive_keyword in key_lower
                for sensitive_keyword in settings.SENSITIVE_PARAMS
            )
            if is_sensitive:
                filtered_params[key] = "********"
            else:
                filtered_params[key] = value
        return filtered_params

    def get_route_handler(self) -> Callable:
        """
        :return:
        """
        origin_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            """

            :param request:
            :return:
            """
            # Before controller, get request body
            start = time.time()
            request_body = await request.body()
            # Filter sensitive parameters from query params
            filtered_params = self.filter_sensitive_params(dict(request.query_params))
            request_message = {
                "http.request.method": request.method,
                "http.request.path": request.url.path,
                "http.request.params": filtered_params
            }
            if request.method in ("POST", "PUT"):
                try:
                    request_message["http.request.body"] = request_body.decode()
                except Exception as exc:  # noqa
                    logger.warning(exc)
                    request_message["http.request.body"] = ""
            logger.info(request_message)

            # Execute the controller
            response: Response = await origin_handler(request)
            try:
                # After controller process, get response status, body
                try:
                    response_body = response.body.decode()
                except Exception as exc:  # noqa
                    logger.warning(exc)
                    response_body = ""

                response_message = {
                    "response.type": type(response).__name__,
                    "response.status_code": response.status_code,
                    "response.duration": round((time.time() - start) * 1000),
                    "response.body": response_body,
                }
                logger.info(response_message)
                return response
            except Exception as exc:
                logger.warning(exc)
                return response

        return route_handler
