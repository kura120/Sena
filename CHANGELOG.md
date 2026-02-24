# Changelog

All notable changes to Sena will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Sena
- Self-evolving AI assistant core
- Memory system with SQLite persistence
- Extension manager with auto-loading
- FastAPI backend with WebSocket support
- React-based debug dashboard
- Dark-themed UI with 6 main tabs (Chat, Memory, Extensions, Telemetry, Logs, Processing)
- Node.js launcher for easy distribution
- Professional Windows executable support
- Loader window server output panel with autoscroll and log sanitization
- Logs UI: grouped chat events, request metadata panel, JSON/Markdown rendering, copy button
- Chat UI markdown rendering with syntax highlighting and session tabs
- Memory API: recent memories endpoint and explicit "remember this" capture
- mem0 library-mode integration with Ollama checks and health gating

### Features
- **LLM Router**: Intent-based routing to appropriate models
- **Memory System**: Short-term and long-term memory with embeddings
- **Extensions**: Core extensions (file_search, web_search) with hot-reload
- **Telemetry**: Real-time metrics and performance tracking
- **Processing Visualization**: 7-step startup sequence with smart timing
- **Health Monitoring**: API health checks and component status
- **WebSocket Support**: Real-time updates for UI

### Technical
- Python 3.10+ support
- Node.js LTS compatibility
- Comprehensive error handling

### Changed
- Loader layout polish and sizing adjustments
- Session-based memory retrieval with session id filtering
- Memory UI now uses recent endpoint when no search query

### Fixed
- Logs noise filtering for /health and internal routes
- Long-term memory availability when mem0 is degraded

### Planned
- Main Sena app UI (separate from debug dashboard)
- Voice input/output support
- Plugin marketplace
- Cloud sync for memory
- Mobile app
- Additional language model support
- Fix the memory API having inconsistencies
---

## Release Process

To create a new release:

1. Update VERSION file with new version number
2. Update this CHANGELOG with changes
3. Commit changes: `git commit -am "Release v1.0.1"`
4. Create git tag: `git tag v1.0.1`
5. Push to GitHub: `git push origin main --tags`
6. GitHub Actions will automatically build and create the release
