# Sena - Project Structure & Architecture

> **Self-Evolving AI Assistant - Complete Development Blueprint**

---

## Table of Contents

1. [Directory Structure](#directory-structure)
2. [Architecture Overview](#architecture-overview)
3. [Module Descriptions](#module-descriptions)
4. [API Specifications](#api-specifications)
5. [Database Schema](#database-schema)
6. [Configuration Files](#configuration-files)
7. [Development Workflow](#development-workflow)
8. [Error Handling System](#error-handling-system)
9. [Memory System (mem0)](#memory-system-mem0)
10. [Extension System](#extension-system)
11. [Bootstrapper & Benchmarking](#bootstrapper--benchmarking)
12. [UI Applications](#ui-applications)
13. [Deployment](#deployment)

---

## Directory Structure

```
sena/
├── .github/                         # GitHub specific files
│   ├── workflows/                   # GitHub Actions CI/CD
│   │   ├── tests.yml                # Run tests on push/PR
│   │   ├── lint.yml                 # Code quality checks
│   │   └── build.yml                # Build and release
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── custom.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS                   # Code ownership
│
├── .vscode/                         # VS Code settings (optional)
│   ├── settings.json
│   ├── launch.json
│   └── extensions.json
│
├── docs/                            # Documentation
│   ├── images/                      # Documentation images
│   ├── API.md                       # API documentation
│   ├── EXTENSIONS.md                # Extension development guide
│   ├── MEMORY.md                    # Memory system guide
│   ├── ARCHITECTURE.md              # System architecture
│   ├── CONTRIBUTING.md              # How to contribute
│   ├── CHANGELOG.md                 # Version history
│   └── TROUBLESHOOTING.md           # Common issues
│
├── src/                             # Source code (alternative to root-level modules)
│   ├── __init__.py
│   ├── main.py                      # Entry point (CLI/Test/Normal modes)
│   │
│   ├── config/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.yaml            # Main configuration
│   │   ├── models.yaml              # LLM model definitions
│   │   ├── extensions.yaml          # Extension registry
│   │   └── logging.yaml             # Logging configuration
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── sena.py                  # Main Sena orchestrator
│   │   ├── bootstrapper.py          # System initialization & benchmarking
│   │   ├── error_handler.py         # Global error handling system
│   │   ├── telemetry.py             # Metrics & analytics
│   │   └── constants.py             # Application constants
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── manager.py               # LLM lifecycle management
│   │   ├── router.py                # Intent-based routing
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base LLM interface
│   │   │   ├── ollama_client.py     # Ollama integration
│   │   │   └── model_registry.py    # Runtime model switching
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── system_prompts.py    # System prompt templates
│   │       └── intent_prompts.py    # Intent classification prompts
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── manager.py               # Memory orchestrator
│   │   ├── mem0_client.py           # mem0 API integration
│   │   ├── short_term.py            # Session buffer (short-term)
│   │   ├── long_term.py             # Persistent memory (long-term)
│   │   ├── retrieval.py             # Smart memory retrieval
│   │   └── embeddings.py            # Vector embedding handler
│   │
│   ├── extensions/
│   │   ├── __init__.py
│   │   ├── manager.py               # Extension lifecycle manager
│   │   ├── loader.py                # Hot-reload system
│   │   ├── validator.py             # Security sandbox
│   │   ├── generator.py             # AI-powered extension creation
│   │   ├── registry.py              # Extension state tracking
│   │   ├── core/                    # Built-in extensions
│   │   │   ├── __init__.py
│   │   │   ├── app_launcher.py
│   │   │   ├── web_search.py
│   │   │   ├── file_manager.py
│   │   │   └── system_info.py
│   │   └── user/                    # User-created extensions
│   │       └── .gitkeep
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py                # FastAPI backend
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── sena.py              # Main Sena endpoints
│   │   │   ├── memory.py            # Memory management endpoints
│   │   │   ├── extensions.py        # Extension management
│   │   │   ├── telemetry.py         # Metrics endpoints
│   │   │   └── debug.py             # Debug/introspection endpoints
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # API authentication
│   │   │   ├── cors.py              # CORS configuration
│   │   │   └── rate_limit.py        # Rate limiting
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py          # Request schemas
│   │   │   └── responses.py         # Response schemas
│   │   └── websocket/
│   │       ├── __init__.py
│   │       └── manager.py           # WebSocket for real-time streaming
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py            # Thread-safe DB connection pool
│   │   ├── migrations/
│   │   │   ├── __init__.py
│   │   │   ├── v1_initial.py
│   │   │   └── v2_telemetry.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── conversation.py      # Conversation history
│   │   │   ├── memory.py            # Memory storage
│   │   │   ├── extension.py         # Extension metadata
│   │   │   ├── telemetry.py         # Metrics & logs
│   │   │   └── benchmark.py         # Benchmark results
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py              # Base repository pattern
│   │       ├── conversation_repo.py
│   │       ├── memory_repo.py
│   │       ├── extension_repo.py
│   │       ├── telemetry_repo.py
│   │       └── benchmark_repo.py
│   │
│   ├── ui/
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   ├── interface.py         # CLI mode interface
│   │   │   └── commands.py          # CLI command handlers
│   │   │
│   │   ├── behind-the-sena/         # Electron debug app
│   │   │   ├── .gitignore
│   │   │   ├── package.json
│   │   │   ├── package-lock.json
│   │   │   ├── electron.js          # Electron main process
│   │   │   ├── preload.js           # Preload script
│   │   │   ├── README.md
│   │   │   ├── public/
│   │   │   │   └── index.html
│   │   │   └── src/
│   │   │       ├── App.jsx          # Main React component
│   │   │       ├── index.jsx
│   │   │       ├── styles/
│   │   │       │   └── main.css
│   │   │       ├── components/
│   │   │       │   ├── Header.jsx
│   │   │       │   ├── ProcessingView.jsx
│   │   │       │   ├── MemoryView.jsx
│   │   │       │   ├── ExtensionView.jsx
│   │   │       │   ├── TelemetryView.jsx
│   │   │       │   ├── LogsView.jsx
│   │   │       │   └── SettingsView.jsx
│   │   │       ├── hooks/
│   │   │       │   ├── useWebSocket.js
│   │   │       │   └── useAPI.js
│   │   │       └── utils/
│   │   │           ├── api.js
│   │   │           └── formatters.js
│   │   │
│   │   └── sena-app/                # Main Electron app (TBD)
│   │       ├── .gitignore
│   │       ├── package.json
│   │       ├── electron.js
│   │       ├── README.md
│   │       └── src/
│   │           └── .gitkeep
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Centralized logging
│       ├── validators.py            # Input validation
│       ├── formatters.py            # Data formatting
│       ├── file_utils.py            # File operations
│       └── system_utils.py          # System information
│
├── tests/                           # Test files
│   ├── __init__.py
│   ├── conftest.py                  # pytest configuration
│   ├── fixtures/                    # Test fixtures and data
│   │   ├── __init__.py
│   │   ├── sample_extensions.py
│   │   └── sample_conversations.json
│   ├── unit/                        # Unit tests
│   │   ├── __init__.py
│   │   ├── test_llm.py
│   │   ├── test_memory.py
│   │   ├── test_extensions.py
│   │   └── test_database.py
│   ├── integration/                 # Integration tests
│   │   ├── __init__.py
│   │   ├── test_e2e.py
│   │   └── test_api.py
│   └── performance/                 # Performance tests
│       ├── __init__.py
│       └── test_benchmarks.py
│
├── scripts/                         # Utility scripts
│   ├── install_models.sh            # Auto-install Ollama models
│   ├── install_models.bat           # Windows version
│   ├── setup_database.py            # Initialize database
│   ├── benchmark.py                 # Manual benchmarking
│   ├── cleanup.py                   # Clean logs/temp files
│   └── dev_setup.py                 # Development environment setup
│
├── data/                            # Runtime data (gitignored except structure)
│   ├── .gitkeep
│   ├── memory/
│   │   ├── .gitkeep
│   │   ├── sena.db                  # SQLite database (gitignored)
│   │   └── vector_store/            # Vector embeddings (gitignored)
│   │       └── .gitkeep
│   ├── logs/
│   │   ├── .gitkeep
│   │   └── sessions/
│   │       └── .gitkeep
│   ├── benchmarks/
│   │   ├── .gitkeep
│   │   └── results.json             # Benchmark history (gitignored)
│   └── extensions/
│       └── generated/               # AI-generated extensions (gitignored)
│           └── .gitkeep
│
├── assets/                          # Static assets
│   ├── icons/
│   │   ├── icon.ico
│   │   └── icon.png
│   └── images/
│       └── banner.png
│
├── build/                           # Build output (gitignored)
│   └── .gitkeep
│
├── dist/                            # Distribution files (gitignored)
│   └── .gitkeep
│
├── .gitignore                       # Git ignore rules
├── .gitattributes                   # Git attributes
├── .editorconfig                    # Editor configuration
├── .env.example                     # Example environment variables
├── README.md                        # Main readme
├── LICENSE                          # License file
├── SECURITY.md                      # Security policy
├── CODE_OF_CONDUCT.md               # Code of conduct
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Development dependencies
├── setup.py                         # Package setup
├── pyproject.toml                   # Python project config
├── pytest.ini                       # Pytest configuration
├── .pylintrc                        # Pylint configuration
└── Makefile                         # Common commands
```

---

## Essential GitHub Files

### `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log
data/logs/*.log*
data/logs/sessions/*.log

# Database
*.db
*.sqlite
*.sqlite3
data/memory/sena.db
data/memory/vector_store/*

# Benchmarks
data/benchmarks/results.json

# Generated extensions
data/extensions/generated/*

# Environment
.env
.env.local

# Testing
.coverage
.pytest_cache/
htmlcov/
.tox/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build
build/
dist/
*.exe
*.dmg
*.pkg

# OS
Thumbs.db
.DS_Store

# Temporary
tmp/
temp/
*.tmp
```

### `.gitattributes`

```gitattributes
# Auto detect text files and perform LF normalization
* text=auto

# Python files
*.py text eol=lf
*.pyx text eol=lf
*.pyi text eol=lf

# JavaScript/JSON files
*.js text eol=lf
*.jsx text eol=lf
*.json text eol=lf

# YAML files
*.yml text eol=lf
*.yaml text eol=lf

# Markdown
*.md text eol=lf

# Shell scripts
*.sh text eol=lf
*.bat text eol=crlf

# Binary files
*.png binary
*.jpg binary
*.ico binary
*.db binary
*.sqlite binary
```

### `.editorconfig`

```ini
# EditorConfig is awesome: https://EditorConfig.org

root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 120

[*.{js,jsx,json,yml,yaml}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

### `SECURITY.md`

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security vulnerabilities to:
- Email: security@yourproject.com
- Use GitHub's private vulnerability reporting

We will respond within 48 hours and provide updates every 5 business days.

## Security Measures

- All user extensions run in sandboxed environment
- No unauthorized file system or network access
- Database connections are encrypted
- API authentication required for sensitive operations
```

### `CODE_OF_CONDUCT.md`

```markdown
# Code of Conduct

## Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

## Our Standards

Examples of behavior that contributes to a positive environment:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

Examples of unacceptable behavior:
- Trolling, insulting/derogatory comments
- Public or private harassment
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

## Enforcement

Violations may be reported to project maintainers. All complaints will be reviewed and investigated.
```

---

## GitHub Actions Workflows

### `.github/workflows/tests.yml`

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### `.github/workflows/lint.yml`

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install pylint black flake8 mypy
        pip install -r requirements.txt
    
    - name: Run Black
      run: black --check src/ tests/
    
    - name: Run Flake8
      run: flake8 src/ tests/ --max-line-length=120
    
    - name: Run Pylint
      run: pylint src/ --fail-under=8.0
    
    - name: Run MyPy
      run: mypy src/ --ignore-missing-imports
```

### `.github/workflows/build.yml`

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executable
      run: |
        pyinstaller --name=Sena --onefile --windowed src/main.py
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/Sena.exe
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Issue Templates

### `.github/ISSUE_TEMPLATE/bug_report.md`

```markdown
---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g. Windows 11]
 - Sena Version: [e.g. 1.0.0]
 - Python Version: [e.g. 3.10.5]
 - Ollama Version: [e.g. 0.1.0]

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other context about the problem.
```

### `.github/ISSUE_TEMPLATE/feature_request.md`

```markdown
---
name: Feature Request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem?**
A clear description of what the problem is.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other context or screenshots about the feature request.
```

### `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Description
Brief description of changes made

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass locally

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added in hard-to-understand areas
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Dependent changes merged and published

## Related Issues
Closes #(issue number)

## Screenshots (if applicable)
```

### `.github/CODEOWNERS`

```
# Default owners for everything
*       @kura120

# Core system
/src/core/          @kura120
/src/llm/           @kura120
/src/memory/        @kura120

# Extensions
/src/extensions/    @kura120

# Documentation
/docs/              @kura120
*.md                @kura120

# Configuration
/config/            @kura120
```

---

## Git Workflow & Best Practices

### Branch Strategy (Git Flow)

**Main Branches:**
- `main` - Production-ready code, always stable
- `develop` - Integration branch for features

**Supporting Branches:**
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes
- `release/*` - Release preparation

**Branch Naming Conventions:**
```
feature/add-memory-retrieval-engine
feature/implement-hot-reload
bugfix/fix-extension-loading-error
bugfix/resolve-database-lock-issue
hotfix/critical-security-patch
release/v1.0.0
```

---

### Complete Git Workflow

#### Starting a New Feature

```bash
# 1. Update your local develop branch
git checkout develop
git pull origin develop

# 2. Create a new feature branch
git checkout -b feature/your-feature-name

# 3. Work on your feature (make changes)
# ... coding ...

# 4. Stage and commit changes
git add .
git commit -m "feat: add your feature description"

# 5. Push to remote
git push origin feature/your-feature-name

# 6. Create Pull Request on GitHub (develop ← feature/your-feature-name)
```

#### Working on a Feature (Daily Workflow)

```bash
# Start of day - sync with develop
git checkout feature/your-feature-name
git fetch origin
git rebase origin/develop  # or git merge origin/develop

# Make changes and commit frequently
git add specific_file.py
git commit -m "feat: implement specific functionality"

# Push your changes
git push origin feature/your-feature-name

# If rebased and already pushed, force push carefully
git push --force-with-lease origin feature/your-feature-name
```

#### Fixing a Bug

```bash
# 1. Create bugfix branch from develop
git checkout develop
git pull origin develop
git checkout -b bugfix/fix-description

# 2. Fix the bug and commit
git add fixed_file.py
git commit -m "fix: resolve specific bug"

# 3. Push and create PR
git push origin bugfix/fix-description
```

#### Handling Hotfixes (Production Bugs)

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix

# 2. Fix the issue
git add patched_file.py
git commit -m "fix: critical production bug"

# 3. Push and create PR to main
git push origin hotfix/critical-fix

# 4. After merging to main, also merge to develop
git checkout develop
git merge hotfix/critical-fix
git push origin develop
```

#### Preparing a Release

```bash
# 1. Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0

# 2. Update version numbers, CHANGELOG, etc.
git add .
git commit -m "chore: bump version to 1.0.0"

# 3. Push and create PR to main
git push origin release/v1.0.0

# 4. After testing, merge to main and tag
git checkout main
git merge release/v1.0.0
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin main --tags

# 5. Merge back to develop
git checkout develop
git merge release/v1.0.0
git push origin develop

# 6. Delete release branch
git branch -d release/v1.0.0
git push origin --delete release/v1.0.0
```

---

### Commit Message Best Practices

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only changes
- `style` - Code style changes (formatting, no logic change)
- `refactor` - Code refactoring
- `perf` - Performance improvements
- `test` - Adding or updating tests
- `build` - Build system or dependencies
- `ci` - CI configuration changes
- `chore` - Other changes (maintenance)
- `revert` - Reverting a previous commit

**Scope (optional):**
- `llm` - LLM module
- `memory` - Memory system
- `extensions` - Extension system
- `api` - API server
- `ui` - User interface
- `db` - Database

**Examples:**

```bash
# Simple commit
git commit -m "feat(memory): add dynamic retrieval engine"

# Detailed commit
git commit -m "feat(extensions): implement hot-reload system

- Add file watcher for extension directory
- Implement module reload mechanism
- Add validation after reload
- Update registry automatically

Closes #45"

# Breaking change
git commit -m "feat(api)!: change authentication method

BREAKING CHANGE: API now requires JWT tokens instead of API keys.
Update your client code to use the new auth method."

# Multiple files
git commit -m "fix(llm): resolve model switching timeout

- Increase switch timeout to 30 seconds
- Add retry logic for failed switches
- Improve error messages

Fixes #123"
```

---

### Pull Request Best Practices

**Before Creating PR:**
```bash
# 1. Ensure your branch is up to date
git fetch origin
git rebase origin/develop  # or git merge origin/develop

# 2. Run all tests locally
pytest tests/

# 3. Run linters
black src/ tests/
flake8 src/ tests/
pylint src/

# 4. Ensure no merge conflicts
git status

# 5. Push final changes
git push origin your-branch-name
```

**PR Title Format:**
```
[TYPE] Brief description of changes

Examples:
[FEAT] Add memory retrieval engine
[FIX] Resolve extension loading error
[DOCS] Update API documentation
```

**PR Description Template:**
Already provided in `.github/PULL_REQUEST_TEMPLATE.md`

**PR Review Process:**

1. **Automated Checks:**
   - All tests must pass
   - Code coverage must not decrease
   - Linters must pass
   - No merge conflicts

2. **Code Review:**
   - At least 1 approval required
   - Address all comments
   - Update based on feedback

3. **Merging:**
   - Use "Squash and merge" for feature branches
   - Use "Merge commit" for release branches
   - Delete branch after merging

---

### Handling Merge Conflicts

```bash
# When pulling/rebasing causes conflicts

# 1. See which files have conflicts
git status

# 2. Open conflicted files and resolve
#    Look for <<<<<<< HEAD markers
#    Choose which changes to keep

# 3. After resolving, stage the files
git add resolved_file.py

# 4. Continue the rebase/merge
git rebase --continue  # if rebasing
git merge --continue   # if merging

# Or abort if needed
git rebase --abort
git merge --abort
```

**Conflict Resolution in IDE:**
- Use VS Code's built-in merge conflict resolver
- Or PyCharm's merge tool
- Always test after resolving conflicts

---

### Stashing Changes

```bash
# Save work in progress without committing
git stash save "WIP: working on feature X"

# List stashes
git stash list

# Apply latest stash
git stash pop

# Apply specific stash
git stash apply stash@{0}

# Drop a stash
git stash drop stash@{0}

# Clear all stashes
git stash clear
```

---

### Useful Git Commands

**Viewing History:**
```bash
# View commit history
git log --oneline --graph --all

# View changes in a commit
git show <commit-hash>

# View file history
git log -p -- src/core/sena.py

# Search commits
git log --grep="memory"
```

**Undoing Changes:**
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Undo changes to a file
git checkout -- filename.py

# Revert a commit (creates new commit)
git revert <commit-hash>
```

**Cleaning Up:**
```bash
# Delete local branches already merged
git branch --merged | grep -v "\*\|main\|develop" | xargs -n 1 git branch -d

# Delete remote-tracking branches that no longer exist
git fetch --prune

# Clean untracked files (dry run)
git clean -n

# Clean untracked files (actually delete)
git clean -f
```

---

### Git Hooks (Optional)

Create `.git/hooks/pre-commit` to run checks before committing:

```bash
#!/bin/bash
# Pre-commit hook

echo "Running pre-commit checks..."

# Run Black
black --check src/ tests/
if [ $? -ne 0 ]; then
    echo "❌ Black formatting check failed"
    exit 1
fi

# Run Flake8
flake8 src/ tests/ --max-line-length=120
if [ $? -ne 0 ]; then
    echo "❌ Flake8 check failed"
    exit 1
fi

# Run tests
pytest tests/unit/ -q
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

echo "✅ All checks passed"
exit 0
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

### Collaboration Best Practices

**Communication:**
- Reference issues in commits: `Fixes #123`, `Closes #456`, `Related to #789`
- Tag reviewers in PRs: `@username please review`
- Be respectful and constructive in code reviews
- Explain "why" not just "what" in PR descriptions

**Code Review Guidelines:**

**For Reviewers:**
- Review within 24 hours if possible
- Check for code quality, not just functionality
- Suggest improvements, don't just criticize
- Approve when ready, don't be too picky
- Use GitHub's suggestion feature for small fixes

**For Authors:**
- Respond to all comments
- Don't take feedback personally
- Ask questions if unclear
- Update PR based on feedback
- Mark conversations as resolved when addressed

**Avoiding Common Mistakes:**
- ❌ Don't commit directly to `main` or `develop`
- ❌ Don't push sensitive data (API keys, passwords)
- ❌ Don't commit large binary files
- ❌ Don't force push to shared branches
- ❌ Don't merge without review
- ✅ Always create a branch for changes
- ✅ Write descriptive commit messages
- ✅ Keep commits small and focused
- ✅ Test before pushing
- ✅ Update documentation with code changes

---

### Repository Maintenance

**Regular Tasks:**
```bash
# Update dependencies monthly
pip list --outdated
npm outdated

# Review and close stale issues
# Use GitHub's stale bot or manual review

# Archive old branches
git branch -a | grep feature/

# Update CHANGELOG.md
# Add entries for each release

# Run security audit
pip-audit
npm audit
```

**Version Tagging:**
```bash
# Create a tag
git tag -a v1.0.0 -m "Release 1.0.0"

# Push tags
git push origin --tags

# Delete a tag
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

**Release Checklist:**
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version numbers bumped
- [ ] Release notes prepared
- [ ] Tag created
- [ ] Build created
- [ ] Release published on GitHub

---

---

## Architecture Overview

### System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENTRY POINT (main.py)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  CLI Mode    │  │  Test Mode   │  │  Normal Mode (TBD)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼──────────────────┼──────────────────────┼──────────────┘
          │                  │                      │
          └──────────────────┴──────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  BOOTSTRAPPER   │
                    │  • Benchmark    │
                    │  • Validate     │
                    │  • Initialize   │
                    └────────┬────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
    ┌─────▼─────┐                      ┌───────▼────────┐
    │ API Server│                      │  Sena Core     │
    │ (FastAPI) │◄────────────────────►│  Orchestrator  │
    └─────┬─────┘                      └───────┬────────┘
          │                                    │
    ┌─────▼──────────┐                         │
    │  WebSocket     │              ┌──────────┴──────────┐
    │  Real-time     │              │                     │
    │  Streaming     │         ┌────▼────┐          ┌────▼────┐
    └────────────────┘         │   LLM   │          │ Memory  │
                               │ Manager │          │ Manager │
                               └────┬────┘          └────┬────┘
                                    │                    │
                         ┌──────────┼────────────┐       │
                         │          │            │       │
                    ┌────▼───┐ ┌───▼────┐ ┌────▼──┐    │
                    │ Fast   │ │Critical│ │ Code  │    │
                    │ Model  │ │ Model  │ │ Model │    │
                    └────────┘ └────────┘ └───────┘    │
                                                        │
                    ┌───────────────────────────────────┘
                    │
         ┌──────────┴───────────┐
         │                      │
    ┌────▼─────┐          ┌────▼─────┐
    │Short-term│          │Long-term │
    │ (Buffer) │          │ (mem0)   │
    └──────────┘          └──────────┘
                               │
                          ┌────▼────┐
                          │ Vector  │
                          │   DB    │
                          └─────────┘
```

### Component Interaction Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│ 1. Error Handler wraps entire flow         │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 2. Intent Router (FunctionGemma)            │
│    • Classify intent                        │
│    • Select LLM model                       │
│    • Identify required extensions           │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 3. Memory Retrieval (Dynamic)               │
│    • Check if memory needed for intent      │
│    • Retrieve relevant context              │
│    • Add to conversation buffer             │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 4. Extension Check                          │
│    • Load required extensions               │
│    • Validate extension compatibility       │
│    • Execute extension if needed            │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 5. LLM Processing                           │
│    • Stream to selected model               │
│    • Real-time output to UI (if Test Mode)  │
│    • Log processing steps                   │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 6. Post-Processing                          │
│    • Extract learnings for long-term memory │
│    • Update telemetry metrics               │
│    • Log conversation to database           │
└─────────────────────────────────────────────┘
    │
    ▼
Response to User
```

---

## Module Descriptions

### Core Modules

#### `core/sena.py`
**Purpose:** Main orchestrator that coordinates all components.

**Responsibilities:**
- Initialize all subsystems (LLM, Memory, Extensions, Telemetry)
- Coordinate the main processing pipeline
- Handle mode switching (CLI, Test, Normal)
- Manage graceful shutdown

**Key Functions Needed:**
- `__init__(mode: str)` - Initialize with specific mode
- `initialize()` - Setup all components with error handling
- `process(user_input: str)` - Main processing pipeline that returns response and metadata
- `shutdown()` - Graceful cleanup of resources

---

#### `core/bootstrapper.py`
**Purpose:** System initialization and benchmarking before Sena starts.

**Responsibilities:**
- Verify all dependencies (Ollama, models, databases)
- Run system validation checks
- Execute performance benchmarks
- Generate startup reports

**Key Functions Needed:**
- `run()` - Execute all bootstrap checks and return results
- `benchmark()` - Run performance tests on all components
- `validate_system()` - Check data integrity and system health

**Bootstrap Checks Required:**
1. Verify Ollama installation and connectivity
2. Check all required models are available
3. Validate database integrity and run migrations
4. Test extension loading
5. Benchmark system performance
6. Initialize memory system (mem0)

---

#### `core/error_handler.py`
**Purpose:** Centralized error handling and recovery system.

**Responsibilities:**
- Catch and process all exceptions
- Log errors to database and files
- Update telemetry metrics
- Attempt automatic recovery when possible
- Generate user-friendly error messages

**Exception Hierarchy:**
- `SenaException` - Base exception for all Sena errors
- `LLMException` - LLM-related errors (timeouts, connection issues)
- `MemoryException` - Memory system errors
- `ExtensionException` - Extension loading/execution errors
- `DatabaseException` - Database operation errors

**Key Functions Needed:**
- `handle_exception(exc, context)` - Central exception handler
- `wrap(func)` - Decorator for automatic error handling
- `attempt_recovery(error)` - Try to recover from specific error types

---

#### `core/telemetry.py`
**Purpose:** Collect and analyze metrics and analytics.

**Responsibilities:**
- Record performance metrics (response times, memory usage)
- Track error rates and patterns
- Monitor extension performance
- Generate performance reports

**Key Functions Needed:**
- `record_metric(name, value, tags)` - Record a metric point
- `record_error(error, context)` - Log error occurrence
- `get_metrics_summary(time_range)` - Get aggregated stats
- `get_performance_trends()` - Analyze trends over time

---

### LLM Module

#### `llm/manager.py`
**Purpose:** Manage LLM lifecycle with runtime model switching.

**Responsibilities:**
- Load and initialize all Ollama models
- Switch between models at runtime
- Handle streaming responses
- Manage model context windows

**Key Functions Needed:**
- `load_models()` - Initialize all configured models
- `switch_model(model_name)` - Hot-swap to different model
- `generate(prompt, model)` - Get response from model
- `stream_generate(prompt, model)` - Stream response in real-time

---

#### `llm/router.py`
**Purpose:** Intent-based routing using FunctionGemma.

**Responsibilities:**
- Classify user intent from input
- Select appropriate model based on intent
- Identify required extensions
- Determine if memory retrieval is needed

**Key Functions Needed:**
- `classify_intent(user_input)` - Return intent classification with metadata
- `select_model(intent)` - Choose best model for the intent type

**Intent Response Format:**
```
{
    'intent_type': str,           # e.g., 'greeting', 'code_request', 'complex_query'
    'recommended_model': str,     # 'fast', 'critical', or 'code'
    'required_extensions': list,  # Extensions needed for this task
    'needs_memory': bool,         # Whether to retrieve memory
    'confidence': float           # Classification confidence
}
```

---

### Memory Module

#### `memory/manager.py`
**Purpose:** Orchestrate short-term and long-term memory with dynamic retrieval.

**Responsibilities:**
- Manage session buffer (short-term)
- Interface with mem0 (long-term)
- Intelligently decide when to retrieve memories
- Extract learnings from conversations

**Key Functions Needed:**
- `should_retrieve(user_input, intent)` - Decide if memory is needed
- `retrieve_relevant(query, k)` - Get k most relevant memories
- `store(content, metadata, type)` - Save to short or long-term
- `extract_learnings(conversation)` - Extract insights for storage

**Dynamic Retrieval Logic:**
Should retrieve when:
- Intent is recall/reference type
- Input contains temporal references ("last time", "yesterday")
- Input has ambiguous pronouns needing context
- User patterns suggest memory is relevant

Should NOT retrieve when:
- Intent is greeting
- Standalone factual questions
- New unrelated topics

---

#### `memory/mem0_client.py`
**Purpose:** Integration layer for mem0 API/self-hosted instance.

**Responsibilities:**
- Connect to mem0 (cloud or self-hosted)
- Add, search, and update memories
- Generate embeddings for semantic search
- Handle memory metadata

**Key Functions Needed:**
- `__init__(api_key)` - Setup cloud or self-hosted connection
- `add_memory(content, metadata)` - Store new memory
- `search(query, k)` - Vector similarity search
- `update_memory(memory_id, content)` - Update existing memory

---

### Extension Module

#### `extensions/manager.py`
**Purpose:** Manage extension lifecycle with hot-reload capability.

**Responsibilities:**
- Load core and user extensions
- Monitor files for changes (hot-reload)
- Generate extensions using AI
- Maintain extension registry

**Key Functions Needed:**
- `load_all()` - Load all extensions from core/ and user/
- `reload_extension(name)` - Hot-reload specific extension
- `generate_extension(description)` - AI-powered extension creation
- `watch_for_changes()` - File watcher for auto-reload

---

#### `extensions/validator.py`
**Purpose:** Security sandbox for validating and testing extensions.

**Responsibilities:**
- Validate extension code for security issues
- Run extensions in isolated environment
- Test with sample inputs
- Monitor resource usage

**Key Functions Needed:**
- `validate_code(code)` - Security checks before loading
- `test_extension(extension)` - Execute with test data

**Security Checks:**
- No unauthorized imports (eval, exec, __import__)
- No unrestricted file system access
- No unrestricted network access
- No infinite loops or excessive resource usage

---

### API Module

#### `api/server.py`
**Purpose:** FastAPI backend for UI communication.

**Endpoints Required:**

**Chat:**
- `POST /api/v1/chat` - Main chat endpoint
- `GET /api/v1/chat/history` - Get conversation history

**Memory:**
- `GET /api/v1/memory/search` - Search memories
- `POST /api/v1/memory/add` - Add memory manually
- `POST /api/v1/memory/edit` - Edit existing memory
- `DELETE /api/v1/memory/{id}` - Delete memory

**Extensions:**
- `GET /api/v1/extensions` - List all extensions
- `POST /api/v1/extensions/reload` - Reload extension
- `POST /api/v1/extensions/generate` - Generate new extension
- `PUT /api/v1/extensions/{name}/toggle` - Enable/disable extension

**Debug:**
- `GET /api/v1/debug/state` - Current processing state
- `GET /api/v1/debug/logs` - Get logs with filters

**Telemetry:**
- `GET /api/v1/telemetry/metrics` - Performance metrics
- `GET /api/v1/telemetry/errors` - Error statistics

**WebSocket:**
- `WS /ws/stream` - Real-time processing updates

---

#### `api/websocket/manager.py`
**Purpose:** Manage WebSocket connections for real-time streaming.

**Responsibilities:**
- Track active connections
- Broadcast updates to all clients
- Send processing state updates
- Handle client subscriptions

**Key Functions Needed:**
- `broadcast(message)` - Send to all connected clients
- `send_processing_update(update)` - Stream processing state
- `send_memory_update(memory)` - Stream memory operations
- `send_log(log)` - Stream log messages

---

### Database Module

#### `database/connection.py`
**Purpose:** Thread-safe database connection pooling.

**Responsibilities:**
- Manage SQLite connection pool
- Provide transaction context managers
- Handle concurrent access safely
- Auto-retry on lock errors

**Key Functions Needed:**
- `get_connection()` - Get connection from pool
- `return_connection(conn)` - Return to pool
- `transaction()` - Context manager for safe transactions

---

## API Specifications

### REST API Endpoints

#### Chat Endpoints

**POST** `/api/v1/chat`
```json
Request:
{
  "message": "string",
  "context": ["string"],
  "mode": "fast|critical|code"
}

Response:
{
  "response": "string",
  "metadata": {
    "model_used": "string",
    "processing_time": 0.0,
    "extensions_used": ["string"],
    "memory_retrieved": ["string"]
  }
}
```

#### Memory Endpoints

**GET** `/api/v1/memory/search?query={query}&k={k}`
```json
Response:
{
  "results": [
    {
      "content": "string",
      "metadata": {},
      "relevance_score": 0.0
    }
  ]
}
```

**POST** `/api/v1/memory/add`
```json
Request:
{
  "content": "string",
  "metadata": {},
  "type": "short|long"
}
```

**POST** `/api/v1/memory/edit`
```json
Request:
{
  "memory_id": "string",
  "content": "string"
}
```

#### Extension Endpoints

**GET** `/api/v1/extensions`
```json
Response:
{
  "extensions": [
    {
      "name": "string",
      "version": "string",
      "status": "active|inactive|error",
      "description": "string"
    }
  ]
}
```

**POST** `/api/v1/extensions/reload`
```json
Request:
{
  "extension_name": "string"
}
```

**POST** `/api/v1/extensions/generate`
```json
Request:
{
  "description": "string"
}

Response:
{
  "extension_name": "string",
  "code": "string",
  "status": "success|validation_failed|test_failed"
}
```

#### Debug Endpoints

**GET** `/api/v1/debug/state`
```json
Response:
{
  "current_processing": {
    "stage": "string",
    "model": "string",
    "progress": 0.0
  },
  "memory_activity": {
    "retrieving": boolean,
    "storing": boolean
  },
  "active_extensions": ["string"]
}
```

**GET** `/api/v1/debug/logs?level={level}&limit={limit}`
```json
Response:
{
  "logs": [
    {
      "timestamp": "string",
      "level": "string",
      "message": "string",
      "context": {}
    }
  ]
}
```

#### Telemetry Endpoints

**GET** `/api/v1/telemetry/metrics?range={range}`
```json
Response:
{
  "metrics": {
    "response_times": {
      "fast_model": 0.0,
      "critical_model": 0.0,
      "code_model": 0.0
    },
    "error_rate": 0.0,
    "extension_success_rate": 0.0
  }
}
```

### WebSocket Events

**Client → Server**

```json
{
  "type": "subscribe",
  "channels": ["processing", "memory", "logs"]
}
```

**Server → Client**

```json
{
  "type": "processing_update",
  "data": {
    "stage": "intent_classification",
    "details": "Analyzing user intent..."
  }
}

{
  "type": "memory_update",
  "data": {
    "action": "retrieving",
    "query": "string",
    "results_count": 0
  }
}

{
  "type": "log",
  "data": {
    "level": "info",
    "message": "string",
    "timestamp": "string"
  }
}
```

---

## Database Schema

### SQLite Tables

```sql
-- Conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_input TEXT NOT NULL,
    sena_response TEXT NOT NULL,
    model_used TEXT,
    processing_time REAL,
    metadata JSON
);

-- Memory (Short-term buffer)
CREATE TABLE memory_short_term (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Memory (Long-term with mem0)
CREATE TABLE memory_long_term (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mem0_id TEXT UNIQUE,
    content TEXT NOT NULL,
    embedding BLOB,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    metadata JSON
);

-- Extensions
CREATE TABLE extensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_loaded DATETIME,
    execution_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    metadata JSON
);

-- Telemetry (Errors)
CREATE TABLE telemetry_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    error_type TEXT NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    context JSON,
    resolved BOOLEAN DEFAULT FALSE
);

-- Telemetry (Metrics)
CREATE TABLE telemetry_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    tags JSON
);

-- Benchmarks
CREATE TABLE benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    component TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    metadata JSON
);

-- Logs
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSON
);

-- Indexes for performance
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_memory_session ON memory_short_term(session_id);
CREATE INDEX idx_telemetry_timestamp ON telemetry_metrics(timestamp);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_level ON logs(level);
```

---

## Configuration Files

### `config/settings.yaml`

```yaml
# Sena Configuration
version: "1.0.0"

# Application Settings
app:
  name: "Sena"
  mode: "normal"  # cli | test | normal
  debug: false
  
# LLM Configuration
llm:
  provider: "ollama"
  base_url: "http://localhost:11434"
  
  models:
    fast:
      name: "gemma2:2b"
      max_tokens: 2048
      temperature: 0.7
    
    critical:
      name: "gpt-oss:120b"
      max_tokens: 4096
      temperature: 0.5
    
    code:
      name: "nemotron-3-nano"
      max_tokens: 8192
      temperature: 0.3
    
    intent_router:
      name: "functiongemma:latest"
      max_tokens: 1024
      temperature: 0.2
  
  # Runtime model switching
  allow_runtime_switch: true
  switch_cooldown: 5  # seconds

# Memory Configuration
memory:
  provider: "mem0"
  
  mem0:
    mode: "self_hosted"  # self_hosted | cloud
    api_key: null  # Required for cloud mode
    
    vector_db:
      provider: "qdrant"  # qdrant | chroma | weaviate
      host: "localhost"
      port: 6333
      collection_name: "sena_memories"
    
    embeddings:
      model: "nomic-embed-text:latest"
      dimension: 768
  
  short_term:
    max_messages: 20
    expire_after: 3600  # seconds
  
  long_term:
    auto_extract: true
    extract_interval: 10  # messages
  
  retrieval:
    dynamic_threshold: 0.6
    max_results: 5

# Extension Configuration
extensions:
  core_path: "extensions/core"
  user_path: "extensions/user"
  generated_path: "data/extensions/generated"
  
  hot_reload: true
  watch_interval: 2  # seconds
  
  security:
    sandbox_enabled: true
    allowed_imports:
      - "os"
      - "sys"
      - "json"
      - "requests"
    blocked_functions:
      - "eval"
      - "exec"
      - "__import__"
  
  generation:
    max_attempts: 3
    test_timeout: 10  # seconds

# API Configuration
api:
  host: "127.0.0.1"
  port: 8000
  workers: 1
  
  cors:
    enabled: true
    origins:
      - "http://localhost:3000"
      - "http://localhost:3001"
  
  rate_limit:
    enabled: true
    requests_per_minute: 60
  
  websocket:
    heartbeat_interval: 30  # seconds
    max_connections: 10

# Database Configuration
database:
  path: "data/memory/sena.db"
  pool_size: 5
  timeout: 30
  
  migrations:
    auto_run: true

# Logging Configuration
logging:
  level: "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL
  
  file:
    enabled: true
    path: "data/logs/sena.log"
    
    rotation:
      type: "size"  # size | time
      max_bytes: 10485760  # 10MB
      backup_count: 5
  
  database:
    enabled: true
    log_level: "WARNING"  # Only log warnings and above to DB
  
  session:
    enabled: true
    path: "data/logs/sessions"
    rotation: "daily"

# Telemetry Configuration
telemetry:
  enabled: true
  
  metrics:
    collect_interval: 60  # seconds
    retention_days: 30
  
  errors:
    auto_report: true
    include_stack_trace: true
  
  performance:
    track_response_times: true
    track_memory_usage: true
    track_extension_performance: true

# Bootstrapper Configuration
bootstrapper:
  run_on_startup: true
  
  checks:
    - "ollama_installed"
    - "models_available"
    - "database_integrity"
    - "extension_loading"
    - "memory_system"
  
  benchmarks:
    run_on_startup: true
    store_results: true
    compare_with_previous: true
    history_limit: 10  # sessions
  
  performance_thresholds:
    model_response_max: 5.0  # seconds
    memory_retrieval_max: 0.5  # seconds
    extension_load_max: 1.0  # seconds

# UI Configuration
ui:
  behind_the_sena:
    port: 3000
    auto_open: false
    
  sena_app:
    port: 3001
    auto_open: true
```

### `config/models.yaml`

```yaml
# LLM Model Definitions
models:
  - name: "gemma2:2b"
    type: "fast"
    provider: "ollama"
    context_window: 8192
    use_cases:
      - "casual_conversation"
      - "quick_responses"
      - "simple_queries"
  
  - name: "gpt-oss:120b"
    type: "critical"
    provider: "ollama"
    context_window: 32768
    use_cases:
      - "complex_reasoning"
      - "deep_analysis"
      - "critical_decisions"
  
  - name: "nemotron-3-nano"
    type: "code"
    provider: "ollama"
    context_window: 16384
    use_cases:
      - "code_generation"
      - "code_analysis"
      - "technical_tasks"
  
  - name: "functiongemma:latest"
    type: "router"
    provider: "ollama"
    context_window: 4096
    use_cases:
      - "intent_classification"
      - "function_calling"

# Intent → Model Mapping
intent_routing:
  greetings:
    model: "fast"
    extensions: []
    needs_memory: false
  
  general_conversation:
    model: "fast"
    extensions: []
    needs_memory: true
  
  complex_query:
    model: "critical"
    extensions: []
    needs_memory: true
  
  code_request:
    model: "code"
    extensions: ["file_manager"]
    needs_memory: true
  
  system_command:
    model: "fast"
    extensions: ["app_launcher", "system_info"]
    needs_memory: false
  
  web_search:
    model: "fast"
    extensions: ["web_search"]
    needs_memory: false
```

### `config/extensions.yaml`

```yaml
# Extension Registry
core_extensions:
  - name: "app_launcher"
    version: "1.0.0"
    enabled: true
    description: "Launch applications by name"
    parameters:
      app_name: "Name of application to launch"
  
  - name: "web_search"
    version: "1.0.0"
    enabled: true
    description: "Search the web"
    parameters:
      query: "Search query"
      engine: "Search engine (google, bing)"
  
  - name: "file_manager"
    version: "1.0.0"
    enabled: true
    description: "File operations"
    parameters:
      operation: "Operation type (read, write, delete)"
      path: "File path"
  
  - name: "system_info"
    version: "1.0.0"
    enabled: true
    description: "Get system information"
    parameters:
      info_type: "Type of info (cpu, memory, disk)"

user_extensions: []

# Extension dependencies
dependencies:
  file_manager:
    requires: []
  
  web_search:
    requires: []
```

### `config/logging.yaml`

```yaml
# Logging Configuration
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  
  detailed:
    format: '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] [%(funcName)s] %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  
  json:
    class: 'pythonjsonlogger.jsonlogger.JsonFormatter'
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: standard
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: detailed
    filename: data/logs/sena.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
  
  database:
    class: utils.logger.DatabaseHandler
    level: WARNING
    formatter: json
  
  session:
    class: logging.handlers.TimedRotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: data/logs/sessions/session.log
    when: 'midnight'
    interval: 1
    backupCount: 30

loggers:
  sena:
    level: DEBUG
    handlers: [console, file, database, session]
    propagate: false
  
  llm:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  memory:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  extensions:
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
```

---

## Development Workflow

### Initial Setup Instructions

**1. Clone and Setup Virtual Environment**
```bash
git clone https://github.com/yourusername/sena.git
cd sena
python -m venv venv
```

**Activate virtual environment:**
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

**2. Install Python Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

**3. Install Ollama Models**
Run the installation script or manually install:
```bash
# Windows
scripts\install_models.bat

# Linux/Mac
bash scripts/install_models.sh

# Or manually
ollama pull gemma2:2b
ollama pull gpt-oss:120b
ollama pull nemotron-3-nano
ollama pull functiongemma:latest
ollama pull nomic-embed-text:latest
```

**4. Setup Database**
Run the database initialization script to create schema and tables.
```bash
python scripts/setup_database.py
```

**5. Install Vector Database**
Install and start Qdrant or Chroma for mem0:
```bash
# For Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant

# Or install Chroma
pip install chromadb
```

**6. Install Node Dependencies for UI**
```bash
cd src/ui/behind-the-sena
npm install

cd ../sena-app
npm install
```

**7. Run Bootstrapper**
Test that everything is working:
```bash
python src/main.py --bootstrap
```

**8. First Run in CLI Mode**
```bash
python src/main.py --cli
```

---

### Testing Instructions

**Run All Tests:**
```bash
pytest tests/ -v
```

**Run Specific Test Suites:**
```bash
pytest tests/unit/test_llm.py -v
pytest tests/unit/test_memory.py -v
pytest tests/unit/test_extensions.py -v
```

**Run with Coverage Report:**
```bash
pytest --cov=src/core --cov=src/llm --cov=src/memory --cov=src/extensions tests/
```

**Run Integration Tests:**
```bash
pytest tests/integration/ -v
```

**Run Performance Tests:**
```bash
pytest tests/performance/ -v
```

---

### Development Mode Instructions

**Start Backend API Server:**
```bash
# In development mode with auto-reload
cd src
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

**Start Behind The Sena UI:**
```bash
cd src/ui/behind-the-sena
npm run dev
```

**Start Sena in Test Mode:**
```bash
python src/main.py --test
```
This will:
- Start the API server
- Open the Behind The Sena debug UI
- Enable verbose logging

**Start Sena in CLI Mode:**
```bash
python src/main.py --cli
```
For testing without UI.

---

### Extension Development Workflow

**1. Create Extension File**
Create new file in `src/extensions/user/your_extension.py`

**2. Write Extension Code**
Follow the extension structure documented in Extension System section:
- Add VERSION constant
- Add METADATA dictionary
- Implement execute() function
- Optionally add validate() function

**3. Test Extension**
Create test file or use CLI to test manually

**4. Hot-Reload**
If hot-reload is enabled, changes will be detected automatically.
Otherwise, restart Sena or manually reload via API/UI.

---

### Debugging Tips

**Enable Verbose Logging:**
Set in `src/config/settings.yaml`:
```yaml
logging:
  level: "DEBUG"
```

**Check Logs:**
- File logs: `data/logs/sena.log`
- Session logs: `data/logs/sessions/session_YYYYMMDD.log`
- Database logs: Query `logs` table

**Use Behind The Sena UI:**
- Start in test mode
- Watch real-time processing
- Monitor memory operations
- Check extension execution

**Check Benchmarks:**
Review benchmark results to identify performance issues:
```bash
python scripts/benchmark.py
```

**Use Makefile for Common Tasks:**
```bash
# Run tests
make test

# Run linters
make lint

# Run formatters
make format

# Clean build artifacts
make clean

# Setup dev environment
make dev-setup
```

---

## Error Handling System

### Error Flow

```
Exception Occurs
    │
    ▼
┌─────────────────────────────────────┐
│ Error Handler captures exception    │
└─────────────────────────────────────┘
    │
    ├─► Log to file (detailed)
    │
    ├─► Log to database (warning+)
    │
    ├─► Update telemetry metrics
    │
    ├─► Generate user-friendly message
    │
    └─► Attempt recovery (if possible)
         │
         ├─► Success → Continue
         │
         └─► Failure → Graceful degradation
```

### Error Categories

```python
# 1. Recoverable Errors
class RecoverableError(SenaException):
    """Errors that can be automatically recovered from"""
    # Examples:
    # - Temporary network issues
    # - Model timeout (retry with different model)
    # - Extension not found (skip and continue)

# 2. User Errors
class UserError(SenaException):
    """Errors caused by user input"""
    # Examples:
    # - Invalid command
    # - Missing required parameters
    # - Unsupported file format

# 3. System Errors
class SystemError(SenaException):
    """Critical system errors"""
    # Examples:
    # - Database corruption
    # - Ollama not running
    # - Out of memory

# 4. Extension Errors
class ExtensionError(SenaException):
    """Extension-specific errors"""
    # Examples:
    # - Extension validation failed
    # - Sandbox violation
    # - Extension timeout
```

### Error Context Tracking

```python
# Every error includes rich context
error_context = {
    'timestamp': '2025-01-31T12:34:56',
    'session_id': 'abc123',
    'user_input': 'original user message',
    'processing_stage': 'llm_generation',
    'model_used': 'gpt-oss:120b',
    'extensions_active': ['web_search'],
    'memory_retrieved': 3,
    'stack_trace': '...',
    'system_state': {
        'cpu_usage': 45.2,
        'memory_usage': 2.1,  # GB
        'active_connections': 2
    }
}
```

### Recovery Strategies

```python
class ErrorRecovery:
    async def recover_from_llm_error(self, error: LLMException):
        """
        LLM Error Recovery:
        1. Try fallback model
        2. Reduce context window
        3. Simplify prompt
        4. Return cached response if available
        """
    
    async def recover_from_memory_error(self, error: MemoryException):
        """
        Memory Error Recovery:
        1. Skip memory retrieval
        2. Use short-term only
        3. Continue without context
        """
    
    async def recover_from_extension_error(self, error: ExtensionException):
        """
        Extension Error Recovery:
        1. Disable problematic extension
        2. Use fallback extension
        3. Continue without extension
        """
```

---

## Memory System (mem0)

### Memory Architecture

```
┌─────────────────────────────────────────────┐
│            Memory Manager                   │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │ Short-term   │      │   Long-term     │ │
│  │   (Buffer)   │      │    (mem0)       │ │
│  │              │      │                 │ │
│  │ - Session    │      │ - Persistent    │ │
│  │ - Max 20 msg │      │ - Vector DB     │ │
│  │ - 1hr expire │      │ - Searchable    │ │
│  └──────┬───────┘      └────────┬────────┘ │
│         │                       │          │
│         └───────────┬───────────┘          │
│                     │                      │
│              ┌──────▼──────┐               │
│              │  Retrieval  │               │
│              │   Engine    │               │
│              └─────────────┘               │
└─────────────────────────────────────────────┘
```

### Dynamic Memory Retrieval Logic

The `RetrievalEngine` should intelligently determine when memory retrieval is needed using multiple heuristics:

**1. Intent-based decisions:**
- Questions about past events → Always retrieve
- "Remember when..." phrases → Always retrieve
- Greetings → Never retrieve
- General conversation → Conditional (check context)

**2. Context-based decisions:**
- References to previous topics → Retrieve
- Pronouns without clear antecedents → Retrieve
- Standalone factual questions → Usually skip

**3. User pattern learning:**
- Track topics user frequently asks about
- Retrieve related memories for those topics
- Skip retrieval for new/unrelated topics

**4. Ambiguous cases:**
- Use the fast LLM model to make final decision
- This ensures dynamic, human-like memory recall

### Memory Storage Flow

```
Conversation End
    │
    ▼
Extract Learnings
    │
    ├─► Facts about user
    ├─► Preferences
    ├─► Important events
    └─► Relationships
    │
    ▼
Generate Embeddings
    │
    ▼
Store in mem0
    │
    ├─► Vector DB (semantic search)
    └─► Database (metadata + access tracking)
```

### mem0 Configuration

```yaml
# Self-hosted setup
mem0:
  mode: "self_hosted"
  
  # Vector database
  vector_db:
    provider: "qdrant"
    config:
      host: "localhost"
      port: 6333
      collection: "sena_memories"
      
  # Embedding model
  embeddings:
    model: "nomic-embed-text:latest"
    provider: "ollama"
    dimension: 768
    
  # Memory organization
  organization:
    use_graph: true  # Link related memories
    auto_categorize: true
    
  # Retrieval settings
  retrieval:
    similarity_threshold: 0.6
    reranking: true
    max_results: 5
```

---

## Extension System

### Extension Structure

Every extension must follow this structure:

**Required Constants:**
- `VERSION` - String version number (e.g., "1.0.0")
- `METADATA` - Dictionary containing:
  - `name` - Extension name
  - `description` - What the extension does
  - `author` - Creator name
  - `parameters` - Dictionary of expected parameters with types and descriptions
  - `requires` - List of extension dependencies (can be empty)

**Required Functions:**
- `execute(user_input, context, **kwargs)` - Main function that performs the extension's task
  - Returns: String result
  
**Optional Functions:**
- `validate(user_input, **kwargs)` - Validate inputs before execution
  - Returns: (is_valid: bool, error_message: str)

**Extension File Location:**
- Core extensions: `extensions/core/`
- User extensions: `extensions/user/`
- AI-generated: `data/extensions/generated/`

---

### Hot-Reload System Implementation

The hot-reload system should:

1. **Watch Files:** Monitor extension directories for changes using a file watcher
2. **Detect Changes:** Trigger when `.py` files are modified
3. **Reload Process:**
   - Unload the old module from memory
   - Clear from Python's `sys.modules`
   - Re-import the module
   - Validate the new version
   - Update the registry

4. **Handle Errors:** If reload fails, revert to previous version

---

### AI Extension Generation Process

When generating extensions from user descriptions:

**Step 1: Analyze Description**
- Use the intent router to understand requirements
- Extract needed parameters
- Identify external dependencies

**Step 2: Generate Code**
- Use the Code LLM model
- Provide template structure
- Generate function logic

**Step 3: Validate**
- Run security checks (no eval, exec, restricted imports)
- Verify required metadata is present
- Check for syntax errors

**Step 4: Test**
- Execute in sandbox with test inputs
- Monitor resource usage
- Verify output format

**Step 5: Save & Register**
- Save to generated extensions folder
- Add to extension registry
- Make available for use

**Example Flow:**
```
User: "Create an extension that gets weather for a city"
→ Generate code with weather API integration
→ Validate security (allowed network access)
→ Test with sample cities
→ Save as "weather_lookup.py"
→ Register and make available
```

---

### Extension Dependencies

Extensions can depend on other extensions:

**Dependency Resolution:**
- When loading extension A that requires extension B
- First load extension B
- Then load extension A
- Handle circular dependencies (reject or warn)

**Load Order:**
- Build dependency graph
- Topologically sort extensions
- Load in correct order

---

## Bootstrapper & Benchmarking

### Bootstrapper Checks

The bootstrapper should run these checks before Sena starts:

**1. Ollama Installation Check**
- Verify Ollama is installed
- Check if Ollama service is running
- Test connectivity to localhost:11434

**2. Model Availability Check**
- For each required model:
  - gemma2:2b
  - gpt-oss:120b
  - nemotron-3-nano
  - functiongemma:latest
  - nomic-embed-text:latest
- Verify model is downloaded
- Test model can generate responses

**3. Database Integrity Check**
- Verify database file exists
- Check database schema is up-to-date
- Run any pending migrations
- Test read/write operations
- Check for corrupted data

**4. Extension Validation Check**
- Load all core extensions
- Validate extension structure
- Check for security issues
- Test with sample inputs

**5. Memory System Check**
- Verify vector DB (Qdrant/Chroma) is accessible
- Test embedding generation
- Check mem0 configuration
- Validate storage/retrieval

**6. API Server Check**
- Verify port is available (default 8000)
- Test FastAPI can start
- Check WebSocket functionality

**Output Format:**
Each check should return status with details for reporting to user

---

### Benchmarking System

The benchmark system should measure:

**1. Model Response Times**
- Fast model (gemma2:2b): Average time for 10 simple queries
- Critical model (gpt-oss:120b): Average time for 5 complex queries  
- Code model (nemotron-3-nano): Average time for 3 code generation tasks

**2. Memory System Performance**
- Retrieval speed: Time to retrieve k=5 memories
- Storage speed: Time to store memory
- Embedding generation: Time to generate embeddings

**3. Extension System Performance**
- Load time: Time to load all extensions
- Execution time: Time for each extension to execute
- Hot-reload time: Time to reload an extension

**4. Database Performance**
- Query speed: Time for common queries
- Write speed: Time for inserts/updates
- Concurrent access: Time with multiple connections

**Benchmark Storage:**
- Store last 5-10 benchmark sessions
- Compare current with previous
- Flag significant performance degradation
- Generate trend reports

---

### Performance Thresholds

Define acceptable performance limits:

**Model Response Times:**
- Fast model: < 2.0 seconds
- Critical model: < 8.0 seconds
- Code model: < 10.0 seconds

**Memory Operations:**
- Retrieval: < 0.5 seconds
- Storage: < 0.3 seconds

**Extension Operations:**
- Load time: < 1.0 second per extension
- Execution: Varies by extension

**Database Operations:**
- Query: < 0.1 seconds
- Write: < 0.05 seconds

When thresholds exceeded, flag for investigation.

---

### Auto-Optimization

Based on benchmark results, automatically optimize:

**If Model Too Slow:**
- Suggest switching to smaller/faster model
- Reduce context window size
- Enable response caching

**If Memory Retrieval Slow:**
- Reduce k value (number of results)
- Optimize vector DB indexes
- Cache frequent queries

**If Extensions Slow:**
- Disable unused extensions
- Suggest code optimization
- Monitor for resource leaks

**If Database Slow:**
- Run VACUUM command
- Rebuild indexes
- Suggest moving to faster storage

---

## UI Applications

### Behind The Sena (Debug UI)

**Technology Stack:**
- Electron for desktop app
- React for UI components
- WebSocket for real-time updates
- FastAPI backend (Python)

**Port:** 3000 (configurable)

---

#### Features

**1. Processing View**
- **Live Processing Visualization:** Show current processing stage
- **Pipeline Stages Display:** Visual indicators for each stage (Intent → Memory → Extension → LLM → Post-processing)
- **Model Indicator:** Which model is currently being used
- **Extension Tracking:** Show which extensions are executing
- **Timing Metrics:** How long each stage takes
- **Verbose Toggle:** Switch between simple view and detailed JSON view

**2. Memory View**
- **Memory Search:** Search through stored memories
- **Retrieval Events:** Show when memories are retrieved and which ones
- **Manual Memory Editor:** Add, edit, or delete memories manually
- **Memory Statistics:** Total memories, most accessed, recent additions
- **Short-term Buffer:** View current session context
- **Long-term Storage:** Browse persistent memories

**3. Extension View**
- **Extension List:** Show all loaded extensions (core + user + generated)
- **Status Indicators:** Active, inactive, error states
- **Enable/Disable Toggles:** Turn extensions on/off
- **Hot-Reload Button:** Manually trigger extension reload
- **Generate Extension:** Interface to create new extensions via AI
- **Code Viewer:** View extension source code
- **Execution Logs:** See extension execution history

**4. Telemetry View**
- **Response Time Graphs:** Line charts showing model performance over time
- **Error Frequency Charts:** Bar charts of error types
- **Extension Success Rates:** Pie charts showing extension reliability
- **System Resource Usage:** CPU, Memory, Disk usage graphs
- **Performance Trends:** Compare current vs historical performance

**5. Logs View**
- **Live Log Streaming:** Real-time log messages via WebSocket
- **Level Filters:** Filter by DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Search Functionality:** Search through logs
- **Export Logs:** Download logs as file
- **Auto-scroll Toggle:** Follow new logs or stay at current position

**6. Settings View**
- **Configuration Editor:** Edit settings.yaml visually
- **Model Settings:** Change model parameters
- **Memory Settings:** Adjust memory configuration
- **Extension Settings:** Configure extension behavior
- **Apply/Revert:** Save changes or reset to defaults

---

#### WebSocket Communication

**Client subscribes to channels:**
- `processing` - Processing stage updates
- `memory` - Memory operation events
- `logs` - Log messages
- `telemetry` - Metric updates

**Server broadcasts events:**
- Processing updates (stage changes, progress)
- Memory updates (retrievals, storage)
- Log messages (new log entries)
- Telemetry updates (new metrics)

---

#### Component Architecture

**Main Components Needed:**

1. **App.jsx** - Main application container
   - Manages active view state
   - Handles verbose mode toggle
   - Coordinates WebSocket connection

2. **Header.jsx** - Navigation and controls
   - View switcher
   - Verbose mode toggle
   - Connection status indicator

3. **ProcessingView.jsx** - Live processing visualization
   - Pipeline stage indicators
   - Current model display
   - Metrics display
   - Verbose JSON output (optional)

4. **MemoryView.jsx** - Memory management
   - Search interface
   - Memory list with filters
   - Edit/delete controls
   - Statistics dashboard

5. **ExtensionView.jsx** - Extension management
   - Extension list with status
   - Control buttons
   - Code viewer
   - Generation interface

6. **TelemetryView.jsx** - Metrics dashboard
   - Chart components
   - Time range selector
   - Metric selectors

7. **LogsView.jsx** - Log viewer
   - Log stream display
   - Filter controls
   - Search bar
   - Export button

8. **SettingsView.jsx** - Configuration editor
   - Form components for settings
   - Validation
   - Save/reset controls

---

#### Custom Hooks

**useWebSocket.js**
- Manages WebSocket connection
- Handles reconnection logic
- Provides send function
- Returns connection state and messages

**useAPI.js**
- Wrapper for fetch requests
- Handles errors
- Provides loading states
- Manages authentication (if needed)

---

## Deployment

### Building Installer

**Prerequisites:**
- Install PyInstaller: `pip install pyinstaller`
- Ensure all dependencies are installed
- Test application works in development

**Build Python Executable:**
Use PyInstaller to create standalone executable:
```bash
pyinstaller --name=Sena \
  --onefile \
  --windowed \
  --icon=assets/icon.ico \
  --add-data "config:config" \
  --add-data "extensions/core:extensions/core" \
  --hidden-import=uvicorn \
  main.py
```

**Build Electron Apps:**

For Behind The Sena:
```bash
cd ui/behind-the-sena
npm run build
npm run electron:build
```

For Main Sena App (when ready):
```bash
cd ui/sena-app
npm run build
npm run electron:build
```

---

### Installation Package Structure

Create installer package with this structure:
```
SenaInstaller/
├── Sena.exe                    # Main Python executable
├── config/                     # Default configuration files
├── extensions/
│   └── core/                   # Core extensions
├── ui/
│   ├── behind-the-sena/       # Debug UI executable
│   └── sena-app/              # Main UI executable (TBD)
├── install.bat                # Installation script
├── uninstall.bat              # Uninstallation script
└── README.txt                 # Setup instructions
```

---

### Installation Script Requirements

The installation script should:

1. **Check for Ollama**
   - Verify Ollama is installed
   - Provide download link if not found
   
2. **Install AI Models**
   - Pull all required models using Ollama
   - Show progress for each model

3. **Setup Database**
   - Run database initialization
   - Create required directories

4. **Setup Vector Database**
   - Install/start Qdrant or provide instructions
   - Configure connection

5. **Create Shortcuts**
   - Desktop shortcut for Sena
   - Desktop shortcut for Behind The Sena
   - Start menu entries

6. **Configure Startup (Optional)**
   - Option to run Sena on Windows startup

---

### Distribution Methods

**Option 1: Installer EXE**
- Use Inno Setup or NSIS to create installer
- Include all components
- Handle dependencies automatically

**Option 2: Portable ZIP**
- Package all files in ZIP
- Include manual setup instructions
- Requires user to install Ollama separately

**Option 3: Windows Store (Future)**
- Submit as Windows application
- Handle all dependencies in package

---

### Update Mechanism

**Version Checking:**
- Check for updates on startup (optional)
- Compare local version with remote
- Notify user of available updates

**Update Process:**
- Download new version
- Backup current configuration
- Install update
- Migrate configuration if needed
- Restart application

---

### Deployment Checklist

Before releasing:
- [ ] All tests pass
- [ ] Benchmarks within thresholds
- [ ] Documentation complete
- [ ] Installation tested on clean system
- [ ] Uninstallation tested
- [ ] Update process tested
- [ ] Error handling verified
- [ ] Performance acceptable
- [ ] Security review completed
- [ ] License files included

---

## Makefile (Common Commands)

Create a `Makefile` in the root directory with these common commands:

```makefile
.PHONY: help install install-dev test lint format clean dev-setup run-cli run-test build

help:
	@echo "Sena Development Commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make dev-setup     - Setup development environment"
	@echo "  make run-cli       - Run in CLI mode"
	@echo "  make run-test      - Run in test mode"
	@echo "  make build         - Build executable"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	flake8 src/ tests/ --max-line-length=120
	pylint src/ --fail-under=8.0
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

dev-setup:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  Windows: venv\\Scripts\\activate"
	@echo "  Linux/Mac: source venv/bin/activate"
	@echo "Then run: make install-dev"

run-cli:
	python src/main.py --cli

run-test:
	python src/main.py --test

build:
	pyinstaller --name=Sena --onefile --windowed src/main.py
```

**Usage:**
```bash
# Install dependencies
make install-dev

# Run tests
make test

# Format code before committing
make format

# Check code quality
make lint

# Clean build artifacts
make clean
```

---

## Development Roadmap

### Phase 1: Core Foundation (Weeks 1-2)
- [ ] Project structure setup
- [ ] Database schema implementation
- [ ] Basic LLM manager
- [ ] Configuration system
- [ ] Error handling framework
- [ ] Logging system

### Phase 2: Memory System (Weeks 3-4)
- [ ] mem0 integration
- [ ] Short-term memory buffer
- [ ] Long-term memory storage
- [ ] Dynamic retrieval engine
- [ ] Memory extraction pipeline

### Phase 3: Extension System (Week 5)
- [ ] Extension loader
- [ ] Hot-reload mechanism
- [ ] Security validator
- [ ] Core extensions
- [ ] Extension registry

### Phase 4: API & UI (Weeks 6-7)
- [ ] FastAPI backend
- [ ] WebSocket streaming
- [ ] Behind The Sena UI
- [ ] Real-time processing view
- [ ] Memory management UI

### Phase 5: Advanced Features (Weeks 8-9)
- [ ] AI extension generation
- [ ] Bootstrapper & benchmarking
- [ ] Auto-optimization
- [ ] Telemetry dashboard
- [ ] Performance monitoring

### Phase 6: Testing & Polish (Week 10)
- [ ] Comprehensive test suite
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Documentation
- [ ] Deployment packaging

---

## Contributing Guidelines

### Code Style Guidelines

**Python:**
- Use type hints for all function parameters and return values
- Write docstrings for all classes and functions
- Follow PEP 8 style guide
- Use async/await for all I/O operations (network, file, database)
- Prefer explicit error handling over silent failures

**JavaScript/React:**
- Use functional components with hooks
- Follow ESLint configuration
- Use meaningful variable names
- Keep components small and focused
- Extract reusable logic into custom hooks

---

### Commit Message Format

Use conventional commit format:
```
<type>: <description>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- refactor: Code refactoring
- test: Adding tests
- chore: Maintenance tasks
```

Examples:
- `feat: Add memory retrieval engine`
- `fix: Resolve extension hot-reload issue`
- `docs: Update API documentation`
- `refactor: Simplify LLM manager`

---

### Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Write/update tests
5. Update documentation
6. Run tests locally
7. Submit pull request with description

**PR Description Should Include:**
- What changes were made and why
- Type of change (bug fix, feature, etc.)
- Testing performed
- Any breaking changes

---

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No console warnings or errors
- [ ] Error handling implemented
- [ ] Performance impact considered

---

## Troubleshooting

### Common Issues and Solutions

**Issue: "Ollama models not found"**

Solution:
1. Verify Ollama is running: Check if service is active
2. Install missing models manually:
   ```bash
   ollama pull gemma2:2b
   ollama pull gpt-oss:120b
   ollama pull nemotron-3-nano
   ollama pull functiongemma:latest
   ollama pull nomic-embed-text:latest
   ```
3. Check Ollama is accessible at localhost:11434

---

**Issue: "Database locked" or "Database is locked" error**

Solution:
1. Close all other Sena instances
2. Check for crashed processes and terminate them
3. If problem persists, run cleanup script to unlock database
4. Ensure no other applications are accessing the database file

---

**Issue: "Memory system initialization failed"**

Solution:
1. Check vector database (Qdrant/Chroma) is running
2. Verify configuration in settings.yaml
3. Test vector DB connection manually
4. Check if port is already in use
5. Review mem0 configuration for errors

---

**Issue: "Extension failed to load"**

Solution:
1. Check extension syntax for errors
2. Verify required metadata is present (VERSION, METADATA, execute function)
3. Review extension in validator for security issues
4. Check extension dependencies are loaded
5. Look at logs for specific error messages

---

**Issue: "API server won't start" or "Port already in use"**

Solution:
1. Check if port 8000 is already in use
2. Change port in settings.yaml
3. Kill process using the port
4. Verify no firewall blocking

---

**Issue: "WebSocket connection failed" in Behind The Sena UI**

Solution:
1. Ensure API server is running
2. Check WebSocket URL in UI matches server
3. Verify CORS settings allow connection
4. Check firewall/antivirus isn't blocking

---

**Issue: "Model response timeout"**

Solution:
1. Check system resources (CPU, RAM)
2. Try smaller model
3. Reduce context window size
4. Increase timeout in configuration
5. Verify Ollama is responding

---

**Issue: "Out of memory" errors**

Solution:
1. Close unnecessary applications
2. Use smaller models (gemma2:2b instead of gpt-oss:120b)
3. Reduce conversation context size
4. Check for memory leaks in extensions
5. Increase system virtual memory

---

**Issue: "Extension generation failed"**

Solution:
1. Check code model is loaded and working
2. Review generated code for syntax errors
3. Check sandbox validation errors
4. Simplify extension description
5. Try generating again (may succeed on retry)

---

**Issue: "Hot-reload not working"**

Solution:
1. Verify hot-reload is enabled in settings.yaml
2. Check file watcher is running
3. Manually trigger reload via API or UI
4. Restart Sena if problem persists

---

**Issue: "Slow performance" or "Response times exceeded thresholds"**

Solution:
1. Run benchmarks to identify bottleneck
2. Check system resources
3. Optimize extensions (disable unused ones)
4. Reduce memory retrieval k value
5. Use faster models for routine tasks
6. Run database VACUUM command
7. Check for background processes consuming resources

---

### Getting Help

**Check Logs First:**
- Review `data/logs/sena.log` for errors
- Check session logs in `data/logs/sessions/`
- Query database `logs` table for detailed errors

**Use Behind The Sena:**
- Start in test mode to see real-time processing
- Check telemetry for performance issues
- Review extension execution logs

**Report Issues:**
- Include Sena version
- Include error messages from logs
- Describe steps to reproduce
- Include system information (OS, RAM, etc.)
- Include configuration (remove sensitive data)