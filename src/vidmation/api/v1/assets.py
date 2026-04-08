"""Asset management API — upload, list, inspect, and delete custom assets.

Custom assets include transitions, overlays, sound effects, intros, outros,
and watermarks that users upload for use in their video productions.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from vidmation.auth.dependencies import optional_user, require_active_user
from vidmation.models.asset import AssetType
from vidmation.models.user import User
from vidmation.services.assets.manager import AssetManager, UPLOADABLE_TYPES

router = APIRouter(prefix="/assets", tags=["assets"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AssetResponse(BaseModel):
    """Public representation of an asset."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    name: str
    asset_type: str
    file_path: str
    file_size: int | None = None
    mime_type: str | None = None
    duration: float | None = None
    thumbnail_path: str | None = None
    is_public: bool = False
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    """Envelope for asset list responses."""

    items: list[AssetResponse]
    total: int


class AssetDeleteResponse(BaseModel):
    detail: str = "Asset deleted"


# ---------------------------------------------------------------------------
# POST /assets/upload — multipart file upload
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    file: UploadFile = File(..., description="The asset file to upload"),
    asset_type: str = Form(..., description="Asset type (transition, overlay, music, sound_effect, intro, outro, watermark)"),
    name: str = Form(..., description="Display name for the asset"),
    tags: str = Form("", description="Comma-separated tags"),
    is_public: bool = Form(False, description="Make this asset visible to all users"),
    user: User = Depends(require_active_user),
):
    """Upload a custom asset file (transition, overlay, SFX, etc.).

    The file is moved into organised storage under ``assets/uploads/{type}/``
    and a database record is created.
    """
    # Validate type early
    if asset_type.lower() not in UPLOADABLE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid asset type '{asset_type}'. Must be one of: {', '.join(sorted(UPLOADABLE_TYPES))}",
        )

    # Write uploaded file to a temporary location
    suffix = Path(file.filename).suffix if file.filename else ""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        mgr = AssetManager()
        try:
            asset = mgr.upload(
                file_path=Path(tmp.name),
                asset_type=asset_type,
                name=name,
                user_id=user.id,
                tags=tag_list,
                is_public=is_public,
            )
            return AssetResponse.model_validate(asset)
        finally:
            mgr.close()

    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    finally:
        # Clean up temp file if it still exists (upload moved it, but just in case)
        tmp_path = Path(tmp.name)
        if tmp_path.exists():
            tmp_path.unlink()


# ---------------------------------------------------------------------------
# GET /assets — list with optional filters
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=AssetListResponse,
)
async def list_assets(
    asset_type: str | None = Query(None, description="Filter by asset type"),
    include_public: bool = Query(True, description="Include built-in/public assets"),
    user: User | None = Depends(optional_user),
):
    """List available assets.

    Authenticated users see their own assets plus public/built-in ones.
    Anonymous users only see public assets.
    """
    mgr = AssetManager()
    try:
        assets = mgr.list_assets(
            asset_type=asset_type,
            user_id=user.id if user else None,
            include_public=include_public,
        )
        items = [AssetResponse.model_validate(a) for a in assets]
        return AssetListResponse(items=items, total=len(items))
    finally:
        mgr.close()


# ---------------------------------------------------------------------------
# GET /assets/{asset_id} — single asset detail
# ---------------------------------------------------------------------------


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
)
async def get_asset(
    asset_id: str,
    user: User | None = Depends(optional_user),
):
    """Get details for a single asset."""
    mgr = AssetManager()
    try:
        asset = mgr.get_asset(asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        # Access control: must be public or owned by the requesting user
        if not asset.is_public and (user is None or asset.user_id != user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        return AssetResponse.model_validate(asset)
    finally:
        mgr.close()


# ---------------------------------------------------------------------------
# DELETE /assets/{asset_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{asset_id}",
    response_model=AssetDeleteResponse,
)
async def delete_asset(
    asset_id: str,
    user: User = Depends(require_active_user),
):
    """Delete an asset.  Only the owner (or an admin) may delete."""
    mgr = AssetManager()
    try:
        asset = mgr.get_asset(asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        # Only owner or admin may delete
        if asset.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to delete this asset")

        mgr.delete_asset(asset_id)
        return AssetDeleteResponse(detail=f"Asset '{asset.name}' deleted")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    finally:
        mgr.close()
