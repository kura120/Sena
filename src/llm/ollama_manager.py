# src/llm/ollama_manager.py
"""
Ollama Process Manager

Owns the Ollama process lifecycle:
- Detects whether Ollama is already running
- Starts Ollama if not running (when manage=True)
- Sets OLLAMA_MAX_LOADED_MODELS and OLLAMA_NUM_PARALLEL before launch
- Verifies model concurrency after preloading
- Shuts down Ollama only if Sena started it (we_started flag)

This is the single source of truth for Ollama process state.
All other modules call get_ollama_manager() — never manage the process directly.
"""

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from src.config.settings import Settings
from src.utils.logger import logger


class OllamaProcessManager:
    """
    Singleton that owns the Ollama process lifecycle.

    Usage:
        manager = get_ollama_manager()
        success, message = await manager.ensure_running(settings)
        if not success:
            raise LLMConnectionError(message)
    """

    _instance: Optional["OllamaProcessManager"] = None

    def __init__(self) -> None:
        self._process: Optional[asyncio.subprocess.Process] = None
        self._we_started: bool = False

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "OllamaProcessManager":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ensure_running(self, settings: Settings) -> tuple[bool, str]:
        """
        Ensure Ollama is running and ready.

        If Ollama is already reachable: returns immediately with
        (True, "already running").

        If Ollama is not reachable and manage=True: locates the binary,
        sets OLLAMA_MAX_LOADED_MODELS / OLLAMA_NUM_PARALLEL to the number
        of unique model names configured, starts the process, and waits
        up to startup_timeout seconds for /api/tags to respond.

        If manage=False and Ollama is not running: returns
        (False, "Ollama is not running and manage=False").

        Args:
            settings: The application Settings instance.

        Returns:
            (success: bool, message: str)
        """
        base_url: str = settings.llm.base_url
        manage: bool = settings.llm.ollama_process.manage
        timeout: int = settings.llm.ollama_process.startup_timeout

        # Fast path — already up
        if await self._is_running(base_url):
            logger.info(f"Ollama already running at {base_url}")
            return True, "already running"

        if not manage:
            return (
                False,
                f"Ollama is not running at {base_url} and ollama_process.manage is False. "
                "Start Ollama manually and restart Sena.",
            )

        # Count unique model names so Ollama can keep them all resident
        unique_names: set[str] = {cfg.name for cfg in settings.llm.models.values() if cfg.name}
        model_slot_count = max(len(unique_names), 1)

        # Locate binary
        binary = self._find_binary()
        if binary is None:
            return (
                False,
                "Ollama binary not found. Install Ollama from https://ollama.ai and ensure it is on PATH.",
            )

        # Build environment: inherit current env, override concurrency vars
        env = os.environ.copy()
        env["OLLAMA_MAX_LOADED_MODELS"] = str(model_slot_count)
        env["OLLAMA_NUM_PARALLEL"] = str(model_slot_count)

        logger.info(
            f"Starting Ollama (binary={binary}, "
            f"OLLAMA_MAX_LOADED_MODELS={model_slot_count}, "
            f"OLLAMA_NUM_PARALLEL={model_slot_count})..."
        )

        try:
            self._process = await asyncio.create_subprocess_exec(
                str(binary),
                "serve",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
            )
            self._we_started = True
        except FileNotFoundError:
            return (
                False,
                f"Failed to launch Ollama at '{binary}'. Ensure Ollama is installed correctly.",
            )
        except Exception as exc:
            return False, f"Failed to start Ollama process: {exc}"

        # Wait for Ollama to become ready
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(1.0)
            if await self._is_running(base_url):
                logger.info(f"Ollama is ready (took {timeout - (deadline - time.monotonic()):.1f}s).")
                return True, "started"

            # If the process died already, no point waiting further
            if self._process.returncode is not None:
                return (
                    False,
                    f"Ollama process exited unexpectedly with code {self._process.returncode} before becoming ready.",
                )

        return (
            False,
            f"Ollama did not become ready within {timeout}s. Check Ollama logs for errors.",
        )

    async def verify_concurrency(
        self,
        base_url: str,
        expected_model_names: list[str],
    ) -> None:
        """
        After model preloading, query GET /api/ps to check how many
        models are currently resident in Ollama's VRAM/memory.

        If fewer are resident than expected, emit a non-fatal WARNING
        telling the user how to fix it. This never raises.

        Args:
            base_url: Ollama base URL (e.g. "http://localhost:11434")
            expected_model_names: List of unique model names that should
                                  all be resident after preloading.
        """
        if not expected_model_names:
            return

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/ps")
                if response.status_code != 200:
                    logger.debug(f"verify_concurrency: /api/ps returned {response.status_code} — skipped.")
                    return

                data = response.json()
                resident: list[str] = [m.get("name", "") for m in data.get("models", [])]

                resident_count = len(resident)
                expected_count = len(expected_model_names)

                if resident_count < expected_count:
                    logger.warning(
                        f"Model concurrency check: only {resident_count}/{expected_count} "
                        f"model(s) are resident in Ollama. "
                        f"Expected: {expected_model_names}. "
                        f"Resident: {resident}. "
                        f"On low-VRAM hardware this is normal (models swap via RAM). "
                        f"To keep all models in VRAM, set "
                        f"OLLAMA_MAX_LOADED_MODELS={expected_count} before starting Ollama."
                    )
                else:
                    logger.info(f"Concurrency OK — {resident_count} model(s) resident: {resident}")

        except Exception as exc:
            # Non-fatal — this is just a diagnostic
            logger.debug(f"verify_concurrency check failed (non-fatal): {exc}")

    async def shutdown(self) -> None:
        """
        Stop Ollama only if Sena started it (we_started=True).

        If Ollama was already running when Sena launched, this is a
        no-op — we must never kill a user's pre-existing Ollama instance.
        """
        if not self._we_started or self._process is None:
            return

        logger.info("Stopping Ollama process (started by Sena)...")
        try:
            self._process.terminate()
            await asyncio.wait_for(self._process.wait(), timeout=10.0)
            logger.info("Ollama process stopped.")
        except asyncio.TimeoutError:
            logger.warning("Ollama did not stop within 10s — killing.")
            try:
                self._process.kill()
                await self._process.wait()
            except Exception as kill_exc:
                logger.warning(f"Failed to kill Ollama process: {kill_exc}")
        except Exception as exc:
            logger.warning(f"Error stopping Ollama: {exc}")
        finally:
            self._process = None
            self._we_started = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _is_running(self, base_url: str) -> bool:
        """Return True if Ollama responds to GET /api/tags within 3s."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def _find_binary(self) -> Optional[Path]:
        """
        Locate the Ollama executable.

        Search order:
        1. PATH (works on all platforms)
        2. %LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe  (Windows default install)
        """
        # PATH search first — covers all platforms and custom installs
        found = shutil.which("ollama")
        if found:
            return Path(found)

        # Windows default installer location
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                candidate = Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe"
                if candidate.exists():
                    return candidate

        return None


def get_ollama_manager() -> OllamaProcessManager:
    """Return the singleton OllamaProcessManager instance."""
    return OllamaProcessManager.get_instance()
