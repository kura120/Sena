# src/core/bootstrapper.py
"""
Bootstrapper - System Initialization and Benchmarking

Runs all startup checks and benchmarks before Sena starts:
- Ollama connectivity and model availability
- Database integrity
- Extension validation
- Memory system initialization
- Performance benchmarking
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from src.config.settings import get_settings
from src.core.constants import ModelType
from src.core.exceptions import (
    BootstrapException,
    OllamaNotRunningError,
    ModelNotAvailableError,
)
from src.database.connection import get_db, DatabaseManager
from src.utils.logger import logger


console = Console()


class CheckStatus(str, Enum):
    """Status of a bootstrap check."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single bootstrap check."""
    name: str
    status: CheckStatus
    message: str = ""
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


@dataclass
class BenchmarkResult:
    """Result of a single benchmark."""
    component: str
    metric_name: str
    value: float
    unit: str = "ms"
    passed: bool = True
    threshold: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "passed": self.passed,
            "threshold": self.threshold,
        }


class Bootstrapper:
    """
    System bootstrapper that validates and benchmarks all components.
    
    Runs before Sena starts to ensure everything is working correctly.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.settings = get_settings()
        self.session_id = str(uuid.uuid4())[:8]
        
        self._check_results: list[CheckResult] = []
        self._benchmark_results: list[BenchmarkResult] = []
        self._db: Optional[DatabaseManager] = None
    
    async def run(self) -> bool:
        """
        Run all bootstrap checks.
        
        Returns:
            True if all critical checks pass, False otherwise
        """
        logger.info(f"Starting bootstrap session: {self.session_id}")
        
        console.print()
        console.print("[bold cyan]━━━ Bootstrap Checks ━━━[/bold cyan]")
        console.print()
        
        # Run checks
        checks = [
            ("Ollama Service", self._check_ollama),
            ("Required Models", self._check_models),
            ("Database", self._check_database),
            ("Memory System", self._check_memory_system),
            ("Extensions", self._check_extensions),
        ]
        
        all_passed = True
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Running checks...", total=len(checks))
            
            for check_name, check_func in checks:
                progress.update(task, description=f"Checking {check_name}...")
                
                result = await self._run_check(check_name, check_func)
                self._check_results.append(result)
                
                # Display result
                self._display_check_result(result)
                
                if result.status == CheckStatus.FAILED:
                    all_passed = False
                
                progress.advance(task)
        
        # Run benchmarks if checks passed
        if all_passed and self.settings.bootstrapper.benchmarks_on_startup:
            console.print()
            console.print("[bold cyan]━━━ Performance Benchmarks ━━━[/bold cyan]")
            console.print()
            
            await self._run_benchmarks()
            self._display_benchmark_results()
        
        # Store results
        if self.settings.bootstrapper.store_benchmark_results:
            await self._store_results()
        
        # Display summary
        self._display_summary()
        
        return all_passed
    
    async def _run_check(
        self,
        name: str,
        check_func: Callable,
    ) -> CheckResult:
        """Run a single check with timing."""
        start_time = time.perf_counter()
        
        try:
            result = await check_func()
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            if isinstance(result, CheckResult):
                result.duration_ms = duration_ms
                return result
            
            return CheckResult(
                name=name,
                status=CheckStatus.PASSED,
                message="Check passed",
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Check '{name}' failed: {e}")
            
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=str(e),
                duration_ms=duration_ms,
            )
    
    async def _check_ollama(self) -> CheckResult:
        """Check if Ollama is running and accessible."""
        base_url = self.settings.llm.base_url
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("models", []))
                    
                    return CheckResult(
                        name="Ollama Service",
                        status=CheckStatus.PASSED,
                        message=f"Connected to Ollama ({model_count} models available)",
                        details={"url": base_url, "model_count": model_count},
                    )
                else:
                    return CheckResult(
                        name="Ollama Service",
                        status=CheckStatus.FAILED,
                        message=f"Ollama returned status {response.status_code}",
                    )
                    
        except httpx.ConnectError:
            return CheckResult(
                name="Ollama Service",
                status=CheckStatus.FAILED,
                message=f"Cannot connect to Ollama at {base_url}. Is Ollama running?",
            )
        except Exception as e:
            return CheckResult(
                name="Ollama Service",
                status=CheckStatus.FAILED,
                message=f"Error checking Ollama: {e}",
            )
    
    async def _check_models(self) -> CheckResult:
        """Check if required models are available."""
        base_url = self.settings.llm.base_url
        required_models = []
        
        # Collect required model names
        for model_type, config in self.settings.llm.models.items():
            required_models.append((model_type, config.name))
        
        # Add embedding model
        required_models.append(("embeddings", self.settings.memory.embeddings.model))
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                
                if response.status_code != 200:
                    return CheckResult(
                        name="Required Models",
                        status=CheckStatus.FAILED,
                        message="Cannot get model list from Ollama",
                    )
                
                data = response.json()
                available_models = [m.get("name", "") for m in data.get("models", [])]
                
                # Check each required model
                missing = []
                found = []
                
                for model_type, model_name in required_models:
                    # Check if model is available (exact match or prefix match)
                    model_found = any(
                        model_name == available or 
                        available.startswith(model_name.split(":")[0])
                        for available in available_models
                    )
                    
                    if model_found:
                        found.append((model_type, model_name))
                    else:
                        missing.append((model_type, model_name))
                
                if missing:
                    missing_list = ", ".join([f"{t}:{n}" for t, n in missing])
                    return CheckResult(
                        name="Required Models",
                        status=CheckStatus.WARNING if found else CheckStatus.FAILED,
                        message=f"Missing models: {missing_list}",
                        details={"found": found, "missing": missing},
                    )
                
                return CheckResult(
                    name="Required Models",
                    status=CheckStatus.PASSED,
                    message=f"All {len(found)} required models available",
                    details={"found": found},
                )
                
        except Exception as e:
            return CheckResult(
                name="Required Models",
                status=CheckStatus.FAILED,
                message=f"Error checking models: {e}",
            )
    
    async def _check_database(self) -> CheckResult:
        """Check database connectivity and integrity."""
        try:
            self._db = await get_db()
            
            # Test basic operations
            stats = await self._db.get_stats()
            
            # Check if tables exist
            expected_tables = [
                "conversations", "memory_short_term", "memory_long_term",
                "extensions", "telemetry_metrics", "telemetry_errors",
                "logs", "benchmarks"
            ]
            
            missing_tables = [t for t in expected_tables if t not in stats]
            
            if missing_tables:
                return CheckResult(
                    name="Database",
                    status=CheckStatus.WARNING,
                    message=f"Missing tables: {missing_tables}",
                    details={"stats": stats, "missing": missing_tables},
                )
            
            return CheckResult(
                name="Database",
                status=CheckStatus.PASSED,
                message=f"Database OK ({stats.get('file_size_mb', 0):.2f} MB)",
                details={"stats": stats},
            )
            
        except Exception as e:
            return CheckResult(
                name="Database",
                status=CheckStatus.FAILED,
                message=f"Database error: {e}",
            )
    
    async def _check_memory_system(self) -> CheckResult:
        """Check memory system (ChromaDB) initialization."""
        try:
            chroma_dir = Path(self.settings.memory.vector_db.persist_dir)
            chroma_dir.mkdir(parents=True, exist_ok=True)
            
            # Try to import and initialize ChromaDB
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(chroma_dir),
                anonymized_telemetry=False,
            ))
            
            # Try to get or create collection
            collection_name = self.settings.memory.vector_db.collection_name
            collection = client.get_or_create_collection(collection_name)
            
            count = collection.count()
            
            return CheckResult(
                name="Memory System",
                status=CheckStatus.PASSED,
                message=f"ChromaDB OK ({count} memories stored)",
                details={"collection": collection_name, "count": count},
            )
            
        except ImportError:
            return CheckResult(
                name="Memory System",
                status=CheckStatus.FAILED,
                message="ChromaDB not installed. Run: pip install chromadb",
            )
        except Exception as e:
            return CheckResult(
                name="Memory System",
                status=CheckStatus.WARNING,
                message=f"Memory system warning: {e}",
            )
    
    async def _check_extensions(self) -> CheckResult:
        """Check extension system."""
        try:
            core_path = Path(self.settings.extensions.core_path)
            user_path = Path(self.settings.extensions.user_path)
            
            # Count extensions
            core_count = 0
            user_count = 0
            errors = []
            
            if core_path.exists():
                for ext_file in core_path.glob("*.py"):
                    if not ext_file.name.startswith("_"):
                        core_count += 1
            
            if user_path.exists():
                for ext_file in user_path.glob("*.py"):
                    if not ext_file.name.startswith("_"):
                        user_count += 1
            
            # Ensure directories exist
            core_path.mkdir(parents=True, exist_ok=True)
            user_path.mkdir(parents=True, exist_ok=True)
            
            total = core_count + user_count
            
            if errors:
                return CheckResult(
                    name="Extensions",
                    status=CheckStatus.WARNING,
                    message=f"{total} extensions found, {len(errors)} with errors",
                    details={"core": core_count, "user": user_count, "errors": errors},
                )
            
            return CheckResult(
                name="Extensions",
                status=CheckStatus.PASSED,
                message=f"{total} extensions found ({core_count} core, {user_count} user)",
                details={"core": core_count, "user": user_count},
            )
            
        except Exception as e:
            return CheckResult(
                name="Extensions",
                status=CheckStatus.WARNING,
                message=f"Extension check warning: {e}",
            )
    
    async def _run_benchmarks(self) -> None:
        """Run performance benchmarks."""
        benchmarks = [
            ("LLM", "fast_model_response", self._benchmark_fast_model),
            ("LLM", "router_model_response", self._benchmark_router_model),
            ("Memory", "embedding_generation", self._benchmark_embeddings),
            ("Database", "write_latency", self._benchmark_db_write),
            ("Database", "read_latency", self._benchmark_db_read),
        ]
        
        thresholds = self.settings.bootstrapper.performance_thresholds
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running benchmarks...", total=len(benchmarks))
            
            for component, metric_name, bench_func in benchmarks:
                progress.update(task, description=f"Benchmarking {component}/{metric_name}...")
                
                try:
                    value = await bench_func()
                    
                    # Determine threshold
                    threshold = None
                    if metric_name.endswith("_response"):
                        threshold = thresholds.model_response_max * 1000  # Convert to ms
                    elif "memory" in component.lower() or "retrieval" in metric_name:
                        threshold = thresholds.memory_retrieval_max * 1000
                    
                    passed = threshold is None or value <= threshold
                    
                    self._benchmark_results.append(BenchmarkResult(
                        component=component,
                        metric_name=metric_name,
                        value=value,
                        unit="ms",
                        passed=passed,
                        threshold=threshold,
                    ))
                    
                except Exception as e:
                    logger.warning(f"Benchmark {component}/{metric_name} failed: {e}")
                    self._benchmark_results.append(BenchmarkResult(
                        component=component,
                        metric_name=metric_name,
                        value=-1,
                        unit="ms",
                        passed=False,
                    ))
                
                progress.advance(task)
    
    async def _benchmark_fast_model(self) -> float:
        """Benchmark fast model response time."""
        base_url = self.settings.llm.base_url
        model_name = self.settings.llm.models["fast"].name
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            start = time.perf_counter()
            
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Say 'hello' in one word.",
                    "stream": False,
                    "options": {"num_predict": 10},
                }
            )
            response.raise_for_status()
            
            return (time.perf_counter() - start) * 1000
    
    async def _benchmark_router_model(self) -> float:
        """Benchmark router model response time."""
        base_url = self.settings.llm.base_url
        model_name = self.settings.llm.models["router"].name
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            start = time.perf_counter()
            
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Classify: 'hello' -> greeting or question?",
                    "stream": False,
                    "options": {"num_predict": 5},
                }
            )
            response.raise_for_status()
            
            return (time.perf_counter() - start) * 1000
    
    async def _benchmark_embeddings(self) -> float:
        """Benchmark embedding generation."""
        base_url = self.settings.llm.base_url
        model_name = self.settings.memory.embeddings.model
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            start = time.perf_counter()
            
            response = await client.post(
                f"{base_url}/api/embeddings",
                json={
                    "model": model_name,
                    "prompt": "This is a test sentence for embedding generation.",
                }
            )
            response.raise_for_status()
            
            return (time.perf_counter() - start) * 1000
    
    async def _benchmark_db_write(self) -> float:
        """Benchmark database write latency."""
        if not self._db:
            self._db = await get_db()
        
        start = time.perf_counter()
        
        await self._db.insert("logs", {
            "timestamp": datetime.now().isoformat(),
            "level": "DEBUG",
            "logger_name": "benchmark",
            "message": "Benchmark write test",
            "context": "{}",
        })
        
        return (time.perf_counter() - start) * 1000
    
    async def _benchmark_db_read(self) -> float:
        """Benchmark database read latency."""
        if not self._db:
            self._db = await get_db()
        
        start = time.perf_counter()
        
        await self._db.fetch_all(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10"
        )
        
        return (time.perf_counter() - start) * 1000
    
    async def _store_results(self) -> None:
        """Store benchmark results in database."""
        if not self._db:
            return
        
        try:
            for result in self._benchmark_results:
                await self._db.insert("benchmarks", {
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "component": result.component,
                    "metric_name": result.metric_name,
                    "metric_value": result.value,
                    "unit": result.unit,
                    "metadata": "{}",
                })
            
            logger.info(f"Stored {len(self._benchmark_results)} benchmark results")
            
        except Exception as e:
            logger.warning(f"Failed to store benchmark results: {e}")
    
    def _display_check_result(self, result: CheckResult) -> None:
        """Display a single check result."""
        status_icons = {
            CheckStatus.PASSED: "[green]✓[/green]",
            CheckStatus.FAILED: "[red]✗[/red]",
            CheckStatus.WARNING: "[yellow]![/yellow]",
            CheckStatus.SKIPPED: "[dim]○[/dim]",
        }
        
        icon = status_icons.get(result.status, "?")
        time_str = f"[dim]({result.duration_ms:.0f}ms)[/dim]"
        
        console.print(f"  {icon} {result.name}: {result.message} {time_str}")
        
        if self.verbose and result.details:
            for key, value in result.details.items():
                console.print(f"      [dim]{key}: {value}[/dim]")
    
    def _display_benchmark_results(self) -> None:
        """Display benchmark results as a table."""
        table = Table(title="Benchmark Results", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Status", justify="center")
        
        for result in self._benchmark_results:
            status = "[green]✓[/green]" if result.passed else "[red]✗[/red]"
            threshold_str = f"{result.threshold:.0f}ms" if result.threshold else "-"
            value_str = f"{result.value:.1f}ms" if result.value >= 0 else "ERROR"
            
            table.add_row(
                result.component,
                result.metric_name,
                value_str,
                threshold_str,
                status,
            )
        
        console.print(table)
    
    def _display_summary(self) -> None:
        """Display bootstrap summary."""
        passed = sum(1 for r in self._check_results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self._check_results if r.status == CheckStatus.FAILED)
        warnings = sum(1 for r in self._check_results if r.status == CheckStatus.WARNING)
        
        console.print()
        
        if failed > 0:
            console.print(Panel(
                f"[red]Bootstrap Failed[/red]\n"
                f"Passed: {passed} | Failed: {failed} | Warnings: {warnings}",
                title="Summary",
                border_style="red",
            ))
        elif warnings > 0:
            console.print(Panel(
                f"[yellow]Bootstrap Completed with Warnings[/yellow]\n"
                f"Passed: {passed} | Warnings: {warnings}",
                title="Summary",
                border_style="yellow",
            ))
        else:
            console.print(Panel(
                f"[green]Bootstrap Successful[/green]\n"
                f"All {passed} checks passed",
                title="Summary",
                border_style="green",
            ))