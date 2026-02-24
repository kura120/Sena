# Workspace Organization

## Quick Navigation

### Master Rules & Context
- `.github/copilot-instructions.md` - Master development guidelines (READ FIRST)
- `.github/PHASES.md` - Current phase tracker and checklist

### Core Source Code
```
src/
├── main.py                      - Entry point
├── api/server.py               - FastAPI backend
├── core/sena.py                - Orchestrator
├── database/                   - Data layer
├── extensions/                 - Extension system
├── llm/                        - LLM management
├── memory/                     - Memory system
└── ui/behind-the-sena/         - React UI
```

### Development Scripts
- `start-dev.bat` - Start dev environment
- `build-standalone.bat` - Build .exe
- `launcher.js` - Application launcher

### Configuration
- `VERSION` - Version number (single source of truth)
- `src/config/settings.yaml` - Settings
- `pyproject.toml` - Python project config
- `requirements.txt` - Dependencies
- `requirements-dev.txt` - Dev dependencies
- `requirements-dist.txt` - Build dependencies

### Testing
- `pytest` - Run tests: `pytest src/ -v`
- `src/tests/` - Test files

### Release & Distribution
- `.github/workflows/release.yml` - CI/CD pipeline
- `CHANGELOG.md` - Release notes
- `VERSION` - Current version
- `LICENSE` - MIT license

### Documentation
- `README.md` - User-facing project info
- `CONTRIBUTING.md` - Contribution guidelines
- `INSTRUCTIONS.md` - Detailed architecture (reference only)

## Typical Workflows

### Starting Development
1. Read `.github/copilot-instructions.md`
2. Check `.github/PHASES.md` for current work
3. Run `start-dev.bat`
4. Create feature branch: `git checkout -b feature/phase2-taskname`

### Making a Release
1. Update `VERSION` file
2. Update `CHANGELOG.md`
3. `git tag v1.0.1`
4. `git push origin main --tags`
5. GitHub Actions handles building/releasing

### Adding Features
1. Code in `src/`
2. Add tests in `src/tests/`
3. Run `pytest src/ -v`
4. Create PR
5. GitHub Actions tests automatically
6. Merge when approved

### Building Locally
```bash
build-standalone.bat    # Creates dist/Sena.exe
```

## File Purpose Reference

| File | Purpose | Edit? |
|------|---------|-------|
| `.github/copilot-instructions.md` | Master rules | Senior only |
| `.github/PHASES.md` | Phase tracker | Team |
| `VERSION` | Version number | Before release |
| `CHANGELOG.md` | Release notes | Before release |
| `src/` | Source code | Yes (main work) |
| `requirements.txt` | Dependencies | As needed |
| `launcher.js` | App launcher | Rarely |
| `README.md` | User docs | Occasionally |

## Common Commands

```bash
# Development
start-dev.bat                       # Start dev environment
pytest src/ -v                      # Run tests
build-standalone.bat                # Build .exe locally

# Git/Release
git tag v1.0.1                      # Create release tag
git push origin main --tags         # Trigger GitHub Actions

# Python
python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload

# React
cd src/ui/behind-the-sena
npm run build                       # Build React UI
```

## Project Layout Summary

```
Efficient, clean, organized for phases

Root:
├── .github/                    - GitHub config + master rules
├── src/                        - Source code (organized by feature)
├── VERSION                     - Version (1 file, read everywhere)
├── CHANGELOG.md                - Release notes
├── CONTRIBUTING.md             - Contribution rules
├── LICENSE                     - MIT
├── launcher.js                 - Launcher app
├── README.md                   - User README
└── requirements*.txt           - Dependencies

No clutter, no unnecessary files.
Everything has purpose.
```

---

**Purpose:** Navigate workspace efficiently, stay organized for phases
