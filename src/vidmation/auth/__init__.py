"""Authentication and authorization package for AIVidio."""

from vidmation.auth.dependencies import (
    get_current_user,
    optional_user,
    require_active_user,
    require_admin,
)
from vidmation.auth.jwt import create_access_token, create_refresh_token, decode_token
from vidmation.auth.password import hash_password, verify_password

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "hash_password",
    "optional_user",
    "require_active_user",
    "require_admin",
    "verify_password",
]
