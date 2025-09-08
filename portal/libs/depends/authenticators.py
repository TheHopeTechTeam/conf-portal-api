"""
Authenticators for the app
"""
from fastapi import Depends

from portal.libs.auth import AccessTokenAuth

check_admin_access_token = Depends(AccessTokenAuth(is_admin=True))
check_access_token = Depends(AccessTokenAuth(is_admin=False))
