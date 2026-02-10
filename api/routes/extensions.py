# src/api/routes/extensions.py
"""Extension API routes for extension management."""

from typing import Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from src.utils.logger import logger
from src.extensions import get_extension_manager

router = APIRouter(prefix="/extensions", tags=["Extensions"])


class ExtensionToggleRequest(BaseModel):
    """Request body for toggling extension status."""
    enabled: bool = Field(..., description="Whether to enable or disable the extension")


class ExtensionGenerateRequest(BaseModel):
    """Request to generate a new extension."""
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=5)
    prompt: str = Field(..., min_length=10)


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List all extensions",
    description="Get list of all loaded extensions (core, user, generated)",
)
async def list_extensions() -> dict[str, Any]:
    """Get list of all loaded extensions."""
    try:
        mgr = get_extension_manager()
        exts = mgr.list()
        return {"status": "success", "extensions": exts, "total": len(exts)}
    except Exception as e:
        logger.error(f"List extensions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{extension_name}",
    response_model=dict[str, Any],
    summary="Get extension details",
    description="Get details of a specific extension",
)
async def get_extension(
    extension_name: str,
) -> dict[str, Any]:
    """Get details of a specific extension."""
    try:
        mgr = get_extension_manager()
        ext = mgr.get(extension_name)
        if not ext:
            raise HTTPException(status_code=404, detail="Extension not found")
        return {"status": "success", "extension": {"name": ext.name, "enabled": ext.enabled, "metadata": ext.metadata or {}}}
    except Exception as e:
        logger.error(f"Get extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{extension_name}/toggle",
    response_model=dict[str, Any],
    summary="Toggle extension status",
    description="Enable or disable an extension",
)
async def toggle_extension(
    extension_name: str,
    request: ExtensionToggleRequest,
) -> dict[str, Any]:
    """Toggle extension enabled/disabled status."""
    try:
        mgr = get_extension_manager()
        if request.enabled:
            mgr.enable(extension_name)
        else:
            mgr.disable(extension_name)
        return {"status": "success", "extension_name": extension_name, "enabled": request.enabled}
    except Exception as e:
        logger.error(f"Toggle extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{extension_name}/reload",
    response_model=dict[str, Any],
    summary="Reload extension",
    description="Hot-reload a specific extension",
)
async def reload_extension_endpoint(
    extension_name: str,
) -> dict[str, Any]:
    """Reload a specific extension."""
    try:
        mgr = get_extension_manager()
        mgr.reload(extension_name)
        return {"status": "success", "extension_name": extension_name, "message": "reloaded"}
    except Exception as e:
        logger.error(f"Reload extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate",
    response_model=dict[str, Any],
    summary="Generate new extension",
    description="Generate a new extension using AI based on description",
)
async def generate_extension_endpoint(
    request: ExtensionGenerateRequest,
) -> dict[str, Any]:
    """Generate a new extension based on description."""
    try:
        if not request.name or not request.description or not request.prompt:
            raise HTTPException(status_code=400, detail="name, description, and prompt are required")

        # Generation is not implemented yet; return a helpful template
        template = f"""# Generated extension: {request.name}\nEXTENSION_METADATA = {{'name': '{request.name}', 'description': '{request.description}', 'version': '0.1.0', 'core': False}}\n\nasync def execute(params):\n    # TODO: implement using prompt:\n    # {request.prompt}\n    return {{'status': 'not_implemented'}}\n"""
        return {"status": "success", "extension_name": request.name, "code": template}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{extension_name}",
    response_model=dict[str, Any],
    summary="Delete extension",
    description="Delete a user or generated extension",
)
async def delete_extension(
    extension_name: str,
) -> dict[str, Any]:
    """Delete an extension."""
    try:
        mgr = get_extension_manager()
        try:
            mgr.remove(extension_name)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Cannot delete core extension")
        return {"status": "success", "extension_name": extension_name, "message": "deleted"}
    except Exception as e:
        logger.error(f"Delete extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{extension_name}/validate",
    response_model=dict[str, Any],
    summary="Validate extension",
    description="Check extension for security issues and syntax errors",
)
async def validate_extension(
    extension_name: str,
) -> dict[str, Any]:
    """Validate an extension."""
    try:
        mgr = get_extension_manager()
        try:
            result = mgr.validate(extension_name)
        except KeyError:
            raise HTTPException(status_code=404, detail="Extension not found")
        return {"status": "success", "extension_name": extension_name, "valid": result.get("valid", False), "issues": result.get("issues", [])}
    except Exception as e:
        logger.error(f"Validate extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))