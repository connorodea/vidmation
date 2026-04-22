"""Voice management routes — list, clone, preview, and delete voices."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from aividio.config.settings import get_settings
from aividio.db.engine import get_session
from aividio.models.voice import Voice
from aividio.services.tts.voice_cloning import VoiceCloner
from aividio.web.templating import get_templates

router = APIRouter()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _voice_repo_list(
    provider: str | None = None,
    cloned_only: bool | None = None,
) -> list[Voice]:
    """Fetch voices from the database with optional filters."""
    from sqlalchemy import select

    session = get_session()
    try:
        stmt = select(Voice).order_by(Voice.created_at.desc())
        if provider:
            stmt = stmt.where(Voice.provider == provider)
        if cloned_only is True:
            stmt = stmt.where(Voice.is_cloned.is_(True))
        elif cloned_only is False:
            stmt = stmt.where(Voice.is_cloned.is_(False))
        return list(session.scalars(stmt).all())
    finally:
        session.close()


def _voice_repo_get(voice_id: str) -> Voice | None:
    """Fetch a single voice by primary key."""
    session = get_session()
    try:
        return session.get(Voice, voice_id)
    finally:
        session.close()


def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    """Save an uploaded file to *dest_dir* and return the resulting path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:12]}_{upload.filename or 'sample.wav'}"
    dest_path = dest_dir / safe_name
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest_path


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def voice_list(
    request: Request,
    provider: str | None = None,
    cloned: str | None = None,
):
    """List all voices with optional filtering."""
    templates = get_templates()

    cloned_only: bool | None = None
    if cloned == "true":
        cloned_only = True
    elif cloned == "false":
        cloned_only = False

    voices = _voice_repo_list(provider=provider, cloned_only=cloned_only)

    return templates.TemplateResponse(
        "voices/list.html",
        {
            "request": request,
            "voices": voices,
            "filter_provider": provider or "",
            "filter_cloned": cloned or "",
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def voice_clone_form(request: Request):
    """Render the voice cloning form."""
    templates = get_templates()
    return templates.TemplateResponse(
        "voices/clone.html",
        {"request": request},
    )


@router.post("/clone")
async def voice_clone(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    provider: str = Form("elevenlabs"),
    samples: list[UploadFile] = File(...),
):
    """Clone a voice from uploaded audio samples.

    Saves samples to disk, calls the VoiceCloner, and stores the result
    in the database.
    """
    settings = get_settings()

    # Save uploaded samples to a temporary directory.
    upload_dir = settings.data_dir / "voice_samples" / uuid.uuid4().hex[:12]
    sample_paths: list[Path] = []
    for sample in samples:
        path = _save_upload(sample, upload_dir)
        sample_paths.append(path)

    # Clone the voice.
    cloner = VoiceCloner(settings=settings)
    try:
        result = cloner.clone_voice(
            audio_samples=sample_paths,
            name=name,
            description=description,
            provider=provider,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        templates = get_templates()
        return templates.TemplateResponse(
            "voices/clone.html",
            {
                "request": request,
                "error": str(exc),
                "name": name,
                "description": description,
                "provider": provider,
            },
            status_code=400,
        )

    # Generate a preview.
    preview_path: str | None = None
    try:
        preview_dir = settings.data_dir / "voice_previews"
        preview_file = cloner.preview_voice(
            voice_id=result["voice_id"],
            provider=provider,
            output_dir=preview_dir,
        )
        preview_path = str(preview_file)
    except Exception:
        pass  # Preview generation is best-effort.

    # Persist to database.
    session = get_session()
    try:
        voice = Voice(
            name=result["name"],
            provider=result["provider"],
            voice_id=result["voice_id"],
            is_cloned=True,
            sample_path=str(sample_paths[0]) if sample_paths else None,
            preview_path=preview_path,
            reference_audio_path=result.get("reference_audio"),
            description=description,
            settings_json={
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": 1.0,
            },
        )
        session.add(voice)
        session.commit()
        session.refresh(voice)
        voice_db_id = voice.id
    finally:
        session.close()

    return RedirectResponse("/voices", status_code=303)


@router.post("/{voice_id}/preview")
async def voice_preview(voice_id: str):
    """Generate a preview for an existing voice and return the audio file."""
    voice = _voice_repo_get(voice_id)
    if not voice:
        return JSONResponse({"error": "Voice not found"}, status_code=404)

    settings = get_settings()
    cloner = VoiceCloner(settings=settings)

    try:
        preview_dir = settings.data_dir / "voice_previews"
        preview_path = cloner.preview_voice(
            voice_id=voice.voice_id,
            provider=voice.provider,
            output_dir=preview_dir,
        )
    except Exception as exc:
        return JSONResponse(
            {"error": f"Preview generation failed: {exc}"},
            status_code=500,
        )

    # Update the voice record with the preview path.
    session = get_session()
    try:
        db_voice = session.get(Voice, voice_id)
        if db_voice:
            db_voice.preview_path = str(preview_path)
            session.commit()
    finally:
        session.close()

    return FileResponse(
        path=str(preview_path),
        media_type="audio/mpeg",
        filename=f"preview_{voice.name}.mp3",
    )


@router.delete("/{voice_id}")
async def voice_delete(voice_id: str):
    """Delete a voice from the database and the provider."""
    voice = _voice_repo_get(voice_id)
    if not voice:
        return JSONResponse({"error": "Voice not found"}, status_code=404)

    settings = get_settings()

    # Delete from the provider (best-effort).
    if voice.is_cloned:
        try:
            cloner = VoiceCloner(settings=settings)
            cloner.delete_cloned_voice(
                voice_id=voice.voice_id, provider=voice.provider
            )
        except Exception:
            pass  # Provider deletion is best-effort.

    # Delete from database.
    session = get_session()
    try:
        db_voice = session.get(Voice, voice_id)
        if db_voice:
            session.delete(db_voice)
            session.commit()
    finally:
        session.close()

    return JSONResponse({"success": True, "deleted": voice_id})
