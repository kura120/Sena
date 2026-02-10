from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional

from src.utils.logger import logger


@dataclass
class Extension:
    name: str
    module: ModuleType
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ExtensionManager:
    """A minimal Extension Manager.

    Responsibilities:
    - Discover extensions in `src/extensions/user` and `src/extensions/generated`
    - Load, reload, enable, disable, and list extensions
    - Provide a simple validation hook
    """

    def __init__(self, base_paths: Optional[List[Path]] = None):
        self._extensions: Dict[str, Extension] = {}
        if base_paths is None:
            repo_root = Path(__file__).parent
            self._search_paths = [repo_root / "user", repo_root / "generated", repo_root / "core"]
        else:
            self._search_paths = base_paths

        logger.info("ExtensionManager initialized")
        # Auto-load core extensions (files under src/extensions/core)
        try:
            core_dir = Path(__file__).parent / "core"
            if core_dir.exists():
                for file in core_dir.glob("*.py"):
                    if file.name.startswith("__"):
                        continue
                    module_name = f"src.extensions.core.{file.stem}"
                    try:
                        self.load(module_name)
                    except Exception:
                        logger.exception(f"Failed to auto-load core extension {module_name}")
        except Exception:
            logger.exception("Error while auto-loading core extensions")

    def discover(self) -> List[str]:
        """Discover available extension module names (dotted import paths)."""
        found: List[str] = []
        rel_base = Path(__file__).parent.parent
        for p in self._search_paths:
            if not p.exists():
                continue
            for file in p.glob("**/*.py"):
                if file.name.startswith("__"):
                    continue
                try:
                    rel = file.relative_to(rel_base)
                    module_name = ".".join(rel.with_suffix("").parts)
                except ValueError:
                    # file is outside repo layout (e.g., tmp_path during tests) - fall back to filename
                    module_name = file.with_suffix("").name
                found.append(module_name)
        return found

    def load(self, module_name: str) -> Extension:
        """Import and register an extension module by its module path."""
        try:
            module = importlib.import_module(module_name)
            meta = getattr(module, "EXTENSION_METADATA", {}) if hasattr(module, "EXTENSION_METADATA") else {}
            ext = Extension(name=module_name, module=module, enabled=True, metadata=meta)
            self._extensions[module_name] = ext
            logger.info(f"Loaded extension: {module_name}")
            return ext
        except Exception as e:
            logger.error(f"Failed to load extension {module_name}: {e}")
            raise

    def reload(self, module_name: str) -> Extension:
        """Reload a previously loaded module."""
        if module_name not in self._extensions:
            raise KeyError(f"Extension not loaded: {module_name}")
        try:
            module = importlib.reload(self._extensions[module_name].module)
            self._extensions[module_name].module = module
            logger.info(f"Reloaded extension: {module_name}")
            return self._extensions[module_name]
        except Exception as e:
            logger.error(f"Failed to reload extension {module_name}: {e}")
            raise

    def enable(self, module_name: str) -> None:
        if module_name in self._extensions:
            self._extensions[module_name].enabled = True
            logger.info(f"Enabled extension: {module_name}")
        else:
            raise KeyError(module_name)

    def disable(self, module_name: str) -> None:
        if module_name in self._extensions:
            self._extensions[module_name].enabled = False
            logger.info(f"Disabled extension: {module_name}")
        else:
            raise KeyError(module_name)

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "enabled": ext.enabled,
                "metadata": ext.metadata or {},
            }
            for name, ext in self._extensions.items()
        ]

    def get(self, module_name: str) -> Optional[Extension]:
        return self._extensions.get(module_name)

    def remove(self, module_name: str) -> None:
        """Remove an extension from the registry. Core extensions are protected."""
        if module_name not in self._extensions:
            raise KeyError(module_name)
        meta = self._extensions[module_name].metadata or {}
        if meta.get("core"):
            raise PermissionError("Cannot remove core extension")
        # attempt to delete module from sys.modules
        try:
            del sys.modules[self._extensions[module_name].module.__name__]
        except Exception:
            pass
        del self._extensions[module_name]

    def validate(self, module_name: str) -> Dict[str, Any]:
        """Run a lightweight validation of an extension's interface.

        It checks for an `execute` callable and returns findings.
        """
        if module_name not in self._extensions:
            raise KeyError(module_name)
        module = self._extensions[module_name].module
        result = {"valid": True, "issues": []}
        if not hasattr(module, "execute") or not callable(getattr(module, "execute")):
            result["valid"] = False
            result["issues"].append("Missing callable 'execute'")
        # Additional checks can be added
        return result


# Provide a singleton instance for convenience
_default_manager: Optional[ExtensionManager] = None


def get_extension_manager() -> ExtensionManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ExtensionManager()
    return _default_manager
