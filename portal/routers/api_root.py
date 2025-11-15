"""
Root router.
"""
from collections import defaultdict
from typing import Any, Dict, Set

from fastapi import APIRouter, Request, status
from fastapi.openapi.utils import get_openapi

from portal.config import settings
from portal.libs.consts.base import SECURITY_SCHEMES
from .apis.v1 import router as api_v1_router

router = APIRouter()
router.include_router(api_v1_router, prefix="/v1")


@router.get(
    path="/healthz"
)
async def healthz():
    """
    Healthcheck endpoint
    :return:
    """
    return {
        "message": "ok"
    }


def extract_schema_refs(obj: Any, refs: Set[str]) -> None:
    """
    Recursively extract all schema references from an object.

    :param obj: The object to extract references from
    :param refs: Set to store found references
    """
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if ref.startswith("#/components/schemas/"):
                schema_name = ref.split("/")[-1]
                refs.add(schema_name)
        for value in obj.values():
            extract_schema_refs(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            extract_schema_refs(item, refs)


def get_all_referenced_schemas(
    schema_name: str,
    schemas: Dict[str, Any],
    visited: Set[str],
    all_refs: Set[str]
) -> None:
    """
    Recursively get all schemas referenced by a given schema.

    :param schema_name: Name of the schema to process
    :param schemas: All available schemas
    :param visited: Set of already visited schema names to avoid cycles
    :param all_refs: Set to store all referenced schema names
    """
    if schema_name in visited or schema_name not in schemas:
        return

    visited.add(schema_name)
    all_refs.add(schema_name)

    schema = schemas[schema_name]
    refs = set()
    extract_schema_refs(schema, refs)

    for ref in refs:
        get_all_referenced_schemas(ref, schemas, visited, all_refs)


@router.get(
    path="/openapi.json",
    status_code=status.HTTP_200_OK,
)
async def custom_openapi(
    request: Request,
) -> dict:
    """

    :param request:
    :return:
    """
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        summary="Conferences Portal API",
        description="API documentation for Conferences Portal",
        routes=request.app.routes,
    )
    raw_paths = openapi_schema["paths"]
    new_paths = defaultdict()
    admin_schema_refs = set()

    # Collect all schema references from admin paths
    for path, methods in raw_paths.items():  # type: str, dict
        if path.startswith("/api/v1") and "admin" in path:
            # Extract schema references from requestBody and responses
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    # Check requestBody
                    if "requestBody" in operation:
                        extract_schema_refs(operation["requestBody"], admin_schema_refs)

                    # Check responses
                    if "responses" in operation:
                        extract_schema_refs(operation["responses"], admin_schema_refs)
        elif path.startswith("/api/v1") and "admin" not in path:
            new_paths[path] = methods

    # Get all schemas and recursively find all referenced schemas
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    admin_schemas = {}
    all_admin_refs = set()

    # Recursively collect all schemas referenced by admin paths
    visited = set()
    for schema_name in admin_schema_refs:
        get_all_referenced_schemas(schema_name, schemas, visited, all_admin_refs)

    # Store admin schemas and remove them from components
    for schema_name in all_admin_refs:
        if schema_name in schemas:
            admin_schemas[schema_name] = schemas[schema_name]
            del schemas[schema_name]

    openapi_schema["paths"] = new_paths
    openapi_schema["components"]["securitySchemes"] = SECURITY_SCHEMES

    return openapi_schema
