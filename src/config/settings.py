# src/config/settings.py
"""
Sena Configuration Settings

Manages all configuration using Pydantic Settings with YAML file support.

Production path resolution:
- When running as a PyInstaller bundle (sys.frozen = True), all user data
  (settings, database, logs, extensions) lives under APPDATA/Sena on Windows
  or ~/.sena on other platforms.
- On first run the bundled default settings.yaml is copied to that location.
- In development mode paths are resolved relative to the project root.
"""

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaProcessConfig(BaseModel):
    """Ollama process management configuration."""

    # When True, Sena will start Ollama automatically if it is not running.
    manage: bool = True
    # Seconds to wait for Ollama to become ready after launch.
    startup_timeout: int = 30


class LLMModelConfig(BaseModel):
    """Configuration for a single LLM model."""

    name: str
    max_tokens: int = 2048
    temperature: float = 0.7
    context_window: int = 8192


class LLMConfig(BaseModel):
    """LLM configuration settings."""

    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    timeout: int = 120

    models: dict[str, LLMModelConfig] = Field(
        default_factory=lambda: {
            "fast": LLMModelConfig(
                name="",
                max_tokens=2048,
                temperature=0.7,
                context_window=8192,
            ),
            "critical": LLMModelConfig(
                name="",
                max_tokens=4096,
                temperature=0.5,
                context_window=32768,
            ),
            "code": LLMModelConfig(
                name="",
                max_tokens=8192,
                temperature=0.3,
                context_window=16384,
            ),
        }
    )

    # How long Ollama keeps the model loaded after the last request.
    # -1 = indefinite (never evict while Ollama is running).
    # Also accepts Ollama duration strings ("5m", "1h").
    # Note: stored as int in settings.yaml — Pydantic accepts both int and str.
    ollama_keep_alive: int | str = -1

    ollama_process: "OllamaProcessConfig" = Field(default_factory=lambda: OllamaProcessConfig())

    # Reasoning model (chain-of-thought, used before FAST model).
    # Empty string = disabled even if reasoning_enabled=True.
    # Configure via Settings → LLM → Reasoning Model.
    reasoning_model: str = ""
    reasoning_enabled: bool = False


class VectorDBConfig(BaseModel):
    """Vector database configuration."""

    provider: str = "chroma"
    persist_dir: str = "data/memory/chroma"
    collection_name: str = "sena_memories"


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration."""

    model: str = "nomic-embed-text:latest"
    dimension: int = 768


class ShortTermMemoryConfig(BaseModel):
    """Short-term memory configuration."""

    max_messages: int = 20
    expire_after: int = 3600


class LongTermMemoryConfig(BaseModel):
    """Long-term memory configuration."""

    auto_extract: bool = True
    extract_interval: int = 10


class RetrievalConfig(BaseModel):
    """Memory retrieval configuration."""

    dynamic_threshold: float = 0.6
    max_results: int = 5
    reranking: bool = True


class PersonalityConfig(BaseModel):
    """Personality system configuration."""

    # Privacy & learning defaults
    inferential_learning_enabled: bool = True
    inferential_learning_requires_approval: bool = True  # Conservative: opt-in approval

    # Auto-approval policy
    auto_approve_enabled: bool = False  # Off by default; user turns on
    auto_approve_threshold: float = 0.85  # Confidence must exceed this to auto-approve
    learning_mode: str = "moderate"  # "conservative" | "moderate" | "aggressive"

    # System prompt token budget (tokens reserved for personality block)
    personality_token_budget: int = 512
    max_fragments_in_prompt: int = 10

    # Compression: when fragment count exceeds this, compress into a summary
    compress_threshold: int = 20


class MemoryConfig(BaseModel):
    """Complete memory configuration."""

    provider: str = "local"
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    short_term: ShortTermMemoryConfig = Field(default_factory=ShortTermMemoryConfig)
    long_term: LongTermMemoryConfig = Field(default_factory=LongTermMemoryConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)


class ExtensionSecurityConfig(BaseModel):
    """Extension security configuration."""

    sandbox_enabled: bool = True
    allowed_imports: list[str] = Field(
        default_factory=lambda: [
            "os",
            "sys",
            "json",
            "re",
            "datetime",
            "pathlib",
            "typing",
            "collections",
            "itertools",
            "functools",
            "math",
            "random",
            "string",
            "urllib",
            "base64",
        ]
    )
    blocked_functions: list[str] = Field(
        default_factory=lambda: [
            "eval",
            "exec",
            "compile",
            "__import__",
            "open",
            "globals",
            "locals",
            "vars",
            "dir",
            "getattr",
            "setattr",
        ]
    )
    max_execution_time: int = 30
    max_memory_mb: int = 256


class ExtensionGenerationConfig(BaseModel):
    """AI extension generation configuration."""

    max_attempts: int = 3
    test_timeout: int = 10
    auto_enable: bool = False


class ExtensionsConfig(BaseModel):
    """Extensions configuration."""

    core_path: str = "src/extensions/core"
    user_path: str = "src/extensions/user"
    generated_path: str = "data/extensions/generated"
    hot_reload: bool = True
    watch_interval: float = 2.0
    security: ExtensionSecurityConfig = Field(default_factory=ExtensionSecurityConfig)
    generation: ExtensionGenerationConfig = Field(default_factory=ExtensionGenerationConfig)


class CORSConfig(BaseModel):
    """CORS configuration."""

    enabled: bool = False
    origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:5173",
            # Electron windows loaded from file:// send Origin: null.
            # Without this entry the CORS middleware blocks every response
            # to the loader/dashboard when running the packaged app.
            "null",
        ]
    )


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = False
    requests_per_minute: int = 60


class WebSocketConfig(BaseModel):
    """WebSocket configuration."""

    heartbeat_interval: int = 30
    max_connections: int = 10


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    cors: CORSConfig = Field(default_factory=CORSConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = "data/memory/sena.db"
    pool_size: int = 5
    timeout: int = 30
    auto_migrate: bool = True


class FileLoggingConfig(BaseModel):
    """File logging configuration."""

    enabled: bool = True
    path: str = "data/logs/sena.log"
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5


class SessionLoggingConfig(BaseModel):
    """Session logging configuration."""

    enabled: bool = True
    path: str = "data/logs/sessions"


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: FileLoggingConfig = Field(default_factory=FileLoggingConfig)
    session: SessionLoggingConfig = Field(default_factory=SessionLoggingConfig)
    database_level: str = "WARNING"


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    collect_interval: int = 60
    retention_days: int = 30


class PerformanceConfig(BaseModel):
    """Performance tracking configuration."""

    track_response_times: bool = True
    track_memory_usage: bool = True
    track_extension_performance: bool = True


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""

    enabled: bool = True
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)


class PerformanceThresholds(BaseModel):
    """Performance thresholds for warnings."""

    model_response_max: float = 5.0
    memory_retrieval_max: float = 0.5
    extension_load_max: float = 1.0


class BootstrapperConfig(BaseModel):
    """Bootstrapper configuration."""

    run_on_startup: bool = True
    benchmarks_on_startup: bool = True
    store_benchmark_results: bool = True
    benchmark_history_limit: int = 10
    performance_thresholds: PerformanceThresholds = Field(default_factory=PerformanceThresholds)


class UIConfig(BaseModel):
    """UI configuration."""

    behind_the_sena_port: int = 3000
    sena_app_port: int = 3001
    auto_open_browser: bool = False


class AppConfig(BaseModel):
    """Application configuration."""

    name: str = "Sena"
    version: str = "1.0.0"
    debug: bool = False


class Settings(BaseSettings):
    """
    Main settings class for Sena.

    Loads configuration from:
    1. Environment variables (highest priority)
    2. YAML configuration file
    3. Default values (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_prefix="SENA_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app: AppConfig = Field(default_factory=AppConfig)

    # Core modules
    llm: LLMConfig = Field(default_factory=LLMConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig)

    # Infrastructure
    api: APIConfig = Field(default_factory=APIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    bootstrapper: BootstrapperConfig = Field(default_factory=BootstrapperConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Settings":
        """
        Load settings from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Settings instance with values from the file
        """
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def to_yaml(self, path: Path | str) -> None:
        """
        Save settings to a YAML file.

        Args:
            path: Path to save the configuration file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)


def get_app_data_dir() -> Path:
    """
    Return the application's writable root directory.

    - Production (PyInstaller, sys.frozen=True):
        Windows → %APPDATA%\\Sena
        Other   → ~/.sena
    - Development:
        Project root  (3 levels up from this file:
        src/config/settings.py → Sena/)
    """
    if getattr(sys, "frozen", False):
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home())) / "Sena"
        else:
            base = Path.home() / ".sena"
        base.mkdir(parents=True, exist_ok=True)
        return base
    # Dev: project root is 2 directories above src/config/
    return Path(__file__).resolve().parents[2]


def resolve_data_path(relative_path: str) -> Path:
    """
    Resolve a relative data path (as stored in settings.yaml) to an absolute
    path using the correct base directory for the current environment.

    Example:
        resolve_data_path("data/memory/sena.db")
        # dev  → <project_root>/data/memory/sena.db
        # prod → %APPDATA%/Sena/data/memory/sena.db
    """
    return get_app_data_dir() / relative_path


def get_config_path() -> Path:
    """
    Return the path to the active settings.yaml file.

    Production:
        %APPDATA%\\Sena\\settings.yaml (or ~/.sena/settings.yaml).
        On first run the bundled default is copied there automatically.

    Development:
        Searches common locations under the project tree and returns the first
        match, falling back to src/config/settings.yaml.
    """
    if getattr(sys, "frozen", False):
        config_path = get_app_data_dir() / "settings.yaml"

        # First-run: copy the bundled default so the user has a real file
        if not config_path.exists():
            # PyInstaller unpacks data files to sys._MEIPASS
            bundled = Path(getattr(sys, "_MEIPASS", "")) / "config" / "settings.yaml"
            if bundled.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bundled, config_path)

        return config_path

    # Development: look in common locations
    candidates = [
        Path(__file__).parent / "settings.yaml",  # src/config/settings.yaml
        Path("src/config/settings.yaml"),  # relative to CWD
        Path.home() / ".sena" / "settings.yaml",  # user home fallback
    ]
    for path in candidates:
        if path.exists():
            return path

    # Default — may not exist yet; Settings.from_yaml handles missing gracefully
    return Path(__file__).parent / "settings.yaml"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance loaded from configuration
    """
    config_path = get_config_path()
    return Settings.from_yaml(config_path)


def reload_settings() -> Settings:
    """
    Reload settings from configuration file.

    Returns:
        Fresh Settings instance
    """
    get_settings.cache_clear()
    return get_settings()
