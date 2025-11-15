"""
Authentication and Authorization Router
"""
import inspect
from typing import List, Optional, Callable, Type

from fastapi import APIRouter
from fastapi.routing import APIRoute

from portal.libs.authorization.auth_config import AuthConfig
from portal.libs.consts.base import ROUTER_SECURITY
from portal.libs.logger import logger
from portal.route_classes.auth_route import AuthRoute


class AuthRouter(APIRouter):
    """
    APIRouter with integrated Authentication and Authorization methods

    This router integrates:
    - Authentication: Token verification
    - Authorization: Permission checking
    """

    def __init__(
        self,
        permissions: Optional[List[str]] = None,
        require_all: Optional[bool] = False,
        require_auth: Optional[bool] = True,
        is_admin: Optional[bool] = False,
        allow_superuser: Optional[bool] = False,
        *args,
        **kwargs
    ):
        """
        Initialize AuthRouter
        Default route_class is AuthRoute if not specified.
        If route_class is specified but doesn't support auth_config,
        it will be validated and potentially replaced when auth configuration is used.
        :param permissions:
        :param require_all:
        :param require_auth:
        :param is_admin:
        :param allow_superuser:
        :param args:
        :param kwargs:
        """
        self._permissions = permissions
        self._require_all = require_all
        self._require_auth = require_auth
        self._is_admin = is_admin
        self._allow_superuser = allow_superuser

        self._default_route_class = kwargs.pop("route_class", AuthRoute)
        self._default_router_security = ROUTER_SECURITY

        # Validate that the route_class supports auth_config if it's not AuthRoute
        if self._default_route_class is not AuthRoute:
            if not self._is_auth_route_compatible(self._default_route_class):
                logger.warning(
                    f"Route class {self._default_route_class.__name__} may not support auth_config. "
                    f"Authentication and authorization will use AuthRoute when auth configuration is specified."
                )

        kwargs["route_class"] = self._default_route_class
        super().__init__(*args, **kwargs)

    @staticmethod
    def _is_auth_route_compatible(route_class: Type[APIRoute]) -> bool:
        """
        Check if route_class supports auth_config parameter
        :param route_class: Route class to check
        :return: True if route_class supports auth_config
        """
        if not inspect.isclass(route_class):
            return False

        # Check if it's AuthRoute or a subclass
        if issubclass(route_class, AuthRoute):
            return True

        # Check if __init__ accepts auth_config parameter
        try:
            sig = inspect.signature(route_class.__init__)
            return "auth_config" in sig.parameters
        except (TypeError, ValueError):
            return False

    # def add_api_route(
    #     self,
    #     path: str,
    #     endpoint: Callable[..., Any],
    #     *,
    #     response_model: Any = Default(None),
    #     status_code: Optional[int] = None,
    #     tags: Optional[List[Union[str, Enum]]] = None,
    #     dependencies: Optional[Sequence[FastAPIDepends]] = None,
    #     summary: Optional[str] = None,
    #     description: Optional[str] = None,
    #     response_description: str = "Successful Response",
    #     responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
    #     deprecated: Optional[bool] = None,
    #     methods: Optional[Union[Set[str], List[str]]] = None,
    #     operation_id: Optional[str] = None,
    #     response_model_include: Optional[IncEx] = None,
    #     response_model_exclude: Optional[IncEx] = None,
    #     response_model_by_alias: bool = True,
    #     response_model_exclude_unset: bool = False,
    #     response_model_exclude_defaults: bool = False,
    #     response_model_exclude_none: bool = False,
    #     include_in_schema: bool = True,
    #     response_class: Union[Type[Response], DefaultPlaceholder] = Default(JSONResponse),
    #     name: Optional[str] = None,
    #     route_class_override: Optional[Type[APIRoute]] = None,
    #     callbacks: Optional[List[BaseRoute]] = None,
    #     openapi_extra: Optional[Dict[str, Any]] = None,
    #     generate_unique_id_function: Union[Callable[[APIRoute], str], DefaultPlaceholder] = Default(generate_unique_id),
    #     auth_config: Optional[AuthConfig] = None,
    #     **kwargs: Any,
    # ) -> None:
    #
    #     # Determine which route_class to use
    #     route_class = route_class_override or self.route_class
    #
    #     # If auth_config is provided, ensure route_class supports it
    #     if auth_config:
    #         if not self._is_auth_route_compatible(route_class):
    #             logger.warning(
    #                 f"Route class {route_class.__name__} doesn't support auth_config. "
    #                 f"Using AuthRoute for route {path}"
    #             )
    #             route_class = AuthRoute
    #
    #     # Merge responses
    #     responses = responses or {}
    #     combined_responses = {**self.responses, **responses}
    #
    #     # Get response class
    #     current_response_class = get_value_or_default(
    #         response_class, self.default_response_class
    #     )
    #
    #     # Merge tags
    #     current_tags = self.tags.copy()
    #     if tags:
    #         current_tags.extend(tags)
    #
    #     # Merge dependencies
    #     current_dependencies = self.dependencies.copy()
    #     if dependencies:
    #         current_dependencies.extend(dependencies)
    #
    #     # Merge callbacks
    #     current_callbacks = self.callbacks.copy()
    #     if callbacks:
    #         current_callbacks.extend(callbacks)
    #
    #     # Get generate_unique_id function
    #     current_generate_unique_id = get_value_or_default(
    #         generate_unique_id_function, self.generate_unique_id_function
    #     )
    #
    #     # Prepare route parameters
    #     route_kwargs = {
    #         "response_model": response_model,
    #         "status_code": status_code,
    #         "tags": current_tags,
    #         "dependencies": current_dependencies,
    #         "summary": summary,
    #         "description": description,
    #         "response_description": response_description,
    #         "responses": combined_responses,
    #         "deprecated": deprecated or self.deprecated,
    #         "methods": methods,
    #         "operation_id": operation_id,
    #         "response_model_include": response_model_include,
    #         "response_model_exclude": response_model_exclude,
    #         "response_model_by_alias": response_model_by_alias,
    #         "response_model_exclude_unset": response_model_exclude_unset,
    #         "response_model_exclude_defaults": response_model_exclude_defaults,
    #         "response_model_exclude_none": response_model_exclude_none,
    #         "include_in_schema": include_in_schema and self.include_in_schema,
    #         "response_class": current_response_class,
    #         "name": name,
    #         "dependency_overrides_provider": self.dependency_overrides_provider,
    #         "callbacks": current_callbacks,
    #         "openapi_extra": openapi_extra,
    #         "generate_unique_id_function": current_generate_unique_id,
    #     }
    #
    #     # Add auth_config if provided and route_class supports it
    #     if auth_config and self._is_auth_route_compatible(route_class):
    #         route_kwargs["auth_config"] = auth_config
    #
    #     # Create route
    #     route = route_class(
    #         self.prefix + path,
    #         endpoint=endpoint,
    #         **route_kwargs
    #     )
    #
    #     self.routes.append(route)

    def _add_route_with_auth(
        self,
        method: str,
        path: str,
        endpoint: Callable,
        auth_config: Optional[AuthConfig],
        **kwargs
    ):
        """
        Add route with authentication and authorization configuration
        :param method: HTTP method
        :param path: Route path
        :param endpoint: Endpoint function
        :param auth_config: Authentication and authorization configuration
        :param kwargs: Additional route parameters
        """
        # Set auth_config as metadata on endpoint function for middleware to access
        openapi_extra = kwargs.pop("openapi_extra", None)
        if auth_config:
            setattr(endpoint, "__auth_config__", auth_config)
            if auth_config.require_auth:
                # Add security scheme to openapi_extra
                if openapi_extra is None:
                    openapi_extra = {}
                security = openapi_extra.get("security", [])
                security.extend(self._default_router_security)
                openapi_extra["security"] = security

        # Extract route_class_override from kwargs if present
        route_class_override = kwargs.pop("route_class_override", None)

        # Call add_api_route with auth_config
        self.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=[method],
            route_class_override=route_class_override or self.route_class,
            openapi_extra=openapi_extra,
            **kwargs
        )

    def get(
        self,
        path: str,
        permissions: Optional[List[str]] = None,
        require_all: Optional[bool] = None,
        require_auth: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        allow_superuser: Optional[bool] = None,
        **kwargs
    ):
        """
        Add GET route with authentication and authorization
        :param path:
        :param permissions:
        :param require_all:
        :param require_auth:
        :param is_admin:
        :param allow_superuser:
        :param kwargs:
        :return:
        """

        def decorator(func: Callable) -> Callable:
            auth_config = None
            if require_auth or self._require_auth or permissions or self._permissions:
                auth_config = AuthConfig(
                    permission_codes=permissions if permissions is not None else self._permissions,
                    require_all=require_all if require_all is not None else self._require_all,
                    require_auth=require_auth if require_auth is not None else self._require_auth,
                    is_admin=is_admin if is_admin is not None else self._is_admin,
                    allow_superuser=allow_superuser if allow_superuser is not None else self._allow_superuser
                )
            self._add_route_with_auth(
                method="GET",
                path=path,
                endpoint=func,
                auth_config=auth_config,
                **kwargs
            )
            return func

        return decorator

    def post(
        self,
        path: str,
        permissions: Optional[List[str]] = None,
        require_all: Optional[bool] = None,
        require_auth: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        allow_superuser: Optional[bool] = None,
        **kwargs
    ):
        """
        Add POST route with authentication and authorization
        :param path:
        :param permissions:
        :param require_all:
        :param require_auth:
        :param is_admin:
        :param allow_superuser:
        :param kwargs:
        :return:
        """

        def decorator(func: Callable) -> Callable:
            auth_config = None
            if require_auth or self._require_auth or permissions or self._permissions:
                auth_config = AuthConfig(
                    permission_codes=permissions if permissions is not None else self._permissions,
                    require_all=require_all if require_all is not None else self._require_all,
                    require_auth=require_auth if require_auth is not None else self._require_auth,
                    is_admin=is_admin if is_admin is not None else self._is_admin,
                    allow_superuser=allow_superuser if allow_superuser is not None else self._allow_superuser
                )
            self._add_route_with_auth(
                method="POST",
                path=path,
                endpoint=func,
                auth_config=auth_config,
                **kwargs
            )
            return func

        return decorator

    def put(
        self,
        path: str,
        permissions: Optional[List[str]] = None,
        require_all: Optional[bool] = None,
        require_auth: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        allow_superuser: Optional[bool] = None,
        **kwargs
    ):
        """
        Add PUT route with authentication and authorization
        :param path:
        :param permissions:
        :param require_all:
        :param require_auth:
        :param is_admin:
        :param allow_superuser:
        :param kwargs:
        :return:
        """

        def decorator(func: Callable) -> Callable:
            auth_config = None
            if require_auth or self._require_auth or permissions or self._permissions:
                auth_config = AuthConfig(
                    permission_codes=permissions if permissions is not None else self._permissions,
                    require_all=require_all if require_all is not None else self._require_all,
                    require_auth=require_auth if require_auth is not None else self._require_auth,
                    is_admin=is_admin if is_admin is not None else self._is_admin,
                    allow_superuser=allow_superuser if allow_superuser is not None else self._allow_superuser
                )
            self._add_route_with_auth(
                method="PUT",
                path=path,
                endpoint=func,
                auth_config=auth_config,
                **kwargs
            )
            return func

        return decorator

    def delete(
        self,
        path: str,
        permissions: Optional[List[str]] = None,
        require_all: Optional[bool] = None,
        require_auth: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        allow_superuser: Optional[bool] = None,
        **kwargs
    ):
        """
        Add DELETE route with authentication and authorization
        :param path:
        :param permissions:
        :param require_all:
        :param require_auth:
        :param is_admin:
        :param allow_superuser:
        :param kwargs:
        :return:
        """

        def decorator(func: Callable) -> Callable:
            auth_config = None
            if require_auth or self._require_auth or permissions or self._permissions:
                auth_config = AuthConfig(
                    permission_codes=permissions if permissions is not None else self._permissions,
                    require_all=require_all if require_all is not None else self._require_all,
                    require_auth=require_auth if require_auth is not None else self._require_auth,
                    is_admin=is_admin if is_admin is not None else self._is_admin,
                    allow_superuser=allow_superuser if allow_superuser is not None else self._allow_superuser
                )
            self._add_route_with_auth(
                method="DELETE",
                path=path,
                endpoint=func,
                auth_config=auth_config,
                **kwargs
            )
            return func

        return decorator

    def patch(
        self,
        path: str,
        permissions: Optional[List[str]] = None,
        require_all: Optional[bool] = None,
        require_auth: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        allow_superuser: Optional[bool] = None,
        **kwargs
    ):
        """
        Add PATCH route with authentication and authorization
        :param path:
        :param permissions:
        :param require_all:
        :param require_auth:
        :param is_admin:
        :param allow_superuser:
        :param kwargs:
        :return:
        """

        def decorator(func: Callable) -> Callable:
            auth_config = None
            if require_auth or self._require_auth or permissions or self._permissions:
                auth_config = AuthConfig(
                    permission_codes=permissions if permissions is not None else self._permissions,
                    require_all=require_all if require_all is not None else self._require_all,
                    require_auth=require_auth if require_auth is not None else self._require_auth,
                    is_admin=is_admin if is_admin is not None else self._is_admin,
                    allow_superuser=allow_superuser if allow_superuser is not None else self._allow_superuser
                )
            self._add_route_with_auth(
                method="PATCH",
                path=path,
                endpoint=func,
                auth_config=auth_config,
                **kwargs
            )
            return func

        return decorator
