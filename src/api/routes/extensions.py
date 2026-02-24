# src/api/routes/extensions.py
"""Extension API routes for extension management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.models.requests import ExtensionToggleRequest
from src.extensions import get_extension_manager
from src.utils.logger import logger

router = APIRouter(prefix="/extensions", tags=["Extensions"])


class ExtensionGenerateRequest(BaseModel):
    """Request to generate a new extension via AI."""

    name: str = Field(..., min_length=1, description="Extension name (snake_case)")
    description: str = Field(..., min_length=5, description="What the extension does")
    prompt: str = Field(..., min_length=10, description="Detailed generation instructions")
    auto_enable: bool = Field(False, description="Enable the extension after generation")


def get_ext_manager():
    """Dependency: return the global ExtensionManager instance."""
    return get_extension_manager()


@router.get(
    "",
    response_model=dict[str, Any],
    summary="List all extensions",
    description="Get list of all loaded extensions (core, user, generated)",
)
async def list_extensions(mgr=Depends(get_ext_manager)) -> dict[str, Any]:
    """Get list of all loaded extensions."""
    try:
        exts = mgr.list()
        return {"status": "success", "extensions": exts, "total": len(exts)}
    except Exception as e:
        logger.error(f"List extensions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{extension_name}",
    response_model=dict[str, Any],
    summary="Get extension details",
    description="Get details of a specific extension by name",
)
async def get_extension(
    extension_name: str,
    mgr=Depends(get_ext_manager),
) -> dict[str, Any]:
    """Get details of a specific extension."""
    try:
        ext = mgr.get(extension_name)
        if not ext:
            raise HTTPException(status_code=404, detail=f"Extension '{extension_name}' not found")
        return {
            "status": "success",
            "extension": {
                "name": ext.name,
                "enabled": ext.enabled,
                "metadata": ext.metadata or {},
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get extension error: {e}", exc_info=True)
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
    mgr=Depends(get_ext_manager),
) -> dict[str, Any]:
    """Toggle extension enabled/disabled status."""
    try:
        if request.enabled:
            mgr.enable(extension_name)
        else:
            mgr.disable(extension_name)
        return {
            "status": "success",
            "extension_name": extension_name,
            "enabled": request.enabled,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Extension '{extension_name}' not found")
    except Exception as e:
        logger.error(f"Toggle extension error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{extension_name}/reload",
    response_model=dict[str, Any],
    summary="Reload extension",
    description="Hot-reload a specific extension from disk",
)
async def reload_extension_endpoint(
    extension_name: str,
    mgr=Depends(get_ext_manager),
) -> dict[str, Any]:
    """Reload a specific extension."""
    try:
        mgr.reload(extension_name)
        return {
            "status": "success",
            "extension_name": extension_name,
            "message": "Extension reloaded successfully",
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Extension '{extension_name}' not found")
    except Exception as e:
        logger.error(f"Reload extension error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate",
    response_model=dict[str, Any],
    summary="Generate new extension",
    description="Generate a new extension using AI based on description and prompt",
)
async def generate_extension_endpoint(
    request: ExtensionGenerateRequest,
) -> dict[str, Any]:
    """Generate a new extension based on description."""
    try:
        # Generation via LLM is not yet implemented — return a typed scaffold
        # so the frontend has something to show.
        template = (
            f"# Generated extension: {request.name}\n"
            f'VERSION = "0.1.0"\n'
            f"METADATA = {{\n"
            f'    "name": "{request.name}",\n'
            f'    "description": "{request.description}",\n'
            f'    "author": "Sena",\n'
            f'    "parameters": {{}},\n'
            f'    "requires": [],\n'
            f"}}\n\n\n"
            f"def execute(user_input: str, context: dict, **kwargs) -> str:\n"
            f"    # TODO: implement using prompt:\n"
            f"    # {request.prompt}\n"
            f'    return f"Result: {{user_input}}"\n\n\n'
            f"def validate(user_input: str, **kwargs) -> tuple[bool, str]:\n"
            f"    if not user_input:\n"
            f'        return False, "Input cannot be empty"\n'
            f'    return True, ""\n'
        )
        return {
            "status": "success",
            "extension_name": request.name,
            "code": template,
            "auto_enable": request.auto_enable,
            "message": "Scaffold generated — LLM generation not yet implemented",
        }
    except Exception as e:
        logger.error(f"Generate extension error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{extension_name}",
    response_model=dict[str, Any],
    summary="Delete extension",
    description="Delete a user or generated extension (core extensions cannot be deleted)",
)
async def delete_extension(
    extension_name: str,
    mgr=Depends(get_ext_manager),
) -> dict[str, Any]:
    """Delete an extension."""
    try:
        mgr.remove(extension_name)
        return {
            "status": "success",
            "extension_name": extension_name,
            "message": "Extension deleted",
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Cannot delete a core extension")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Extension '{extension_name}' not found")
    except Exception as e:
        logger.error(f"Delete extension error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{extension_name}/validate",
    response_model=dict[str, Any],
    summary="Validate extension",
    description="Check an extension for security issues and syntax errors",
)
async def validate_extension(
    extension_name: str,
    mgr=Depends(get_ext_manager),
) -> dict[str, Any]:
    """Validate an extension."""
    try:
        result = mgr.validate(extension_name)
        return {
            "status": "success",
            "extension_name": extension_name,
            "valid": result.get("valid", False),
            "issues": result.get("issues", []),
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Extension '{extension_name}' not found")
    except Exception as e:
        logger.error(f"Validate extension error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
