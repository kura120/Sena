<p align="center">
  <a href="https://github.com/kura120/Sena">
    <!-- Replace this URL with your banner image -->
    <img src="assets/sena-github-banner.png" width="800px" alt="Sena - Self-Evolving AI Assistant">
  </a>
</p>


<p align="center">
  <a href="#introduction">Introduction</a> ·
  <a href="#quickstart">Quick Start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#documentation">Documentation</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg?logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGhlaWdodD0iODgiIHdpZHRoPSI4OCIgeG1sbnM6dj0iaHR0cHM6Ly92ZWN0YS5pby9uYW5vIj48cGF0aCBkPSJNMCAxMi40MDJsMzUuNjg3LTQuODYuMDE2IDM0LjQyMy0zNS42Ny4yMDN6bTM1LjY3IDMzLjUyOWwuMDI4IDM0LjQ1M0wuMDI4IDc1LjQ4LjAyNiA0NS43em00LjMyNi0zOS4wMjVMODcuMzE0IDB2NDEuNTI3bC00Ny4zMTguMzc2em00Ny4zMjkgMzkuMzQ5bC0uMDExIDQxLjM0LTQ3LjMxOC02LjY3OC0uMDY2LTM0LjczOXoiIGZpbGw9IndoaXRlIi8+PC9zdmc+" alt="Windows">
  <img src="https://img.shields.io/badge/Status-Down-red" alt="Down">
  <img src="https://img.shields.io/badge/License-MIT-green.svg?logo=data:image/svg%2bxml;base64,PHN2ZyB3aWR0aD0iMTk3cHgiIGhlaWdodD0iMTk3cHgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgdmVyc2lvbj0iMS4xIj4KICAgIDxjaXJjbGUgY3g9Ijk4IiBjeT0iOTgiIHI9IjkwIiBmaWxsPSJ3aGl0ZSIvPgoJPGNpcmNsZSBjeD0iOTgiIGN5PSI5OCIgcj0iNzgiIGZpbGw9IiM1NTU1NTUiLz4KCTxjaXJjbGUgY3g9Ijk4IiBjeT0iOTgiIHI9IjU1IiBmaWxsPSJ3aGl0ZSIvPgoJPGNpcmNsZSBjeD0iOTgiIGN5PSI5OCIgcj0iMzAiIGZpbGw9IiM1NTU1NTUiLz4KCTxyZWN0IHg9IjExNSIgeT0iODUiIHdpZHRoPSI0NSIgaGVpZ2h0PSIyNSIgZmlsbD0iIzU1NTU1NSIvPgo8L3N2Zz4=" alt="MIT License">
</p>

---

## Introduction

Sena ("che-na") is a self-evolving AI assistant for Windows that combines multiple specialized language models with a dynamic extension system. She understands context, remembers conversations across sessions, and can create new capabilities on demand.

### Core Features

**Multi-LLM Architecture**
- Fast responses for conversation
- Deep reasoning for complex queries
- Code generation for system tasks
- Intelligent routing between models

**Dynamic Extension System**
- Built-in capabilities (app launcher, web search)
- Auto-generated extensions using AI
- Security sandbox for validation
- Version control with rollback

**Persistent Memory**
- Short-term: Session context
- Long-term: Learned preferences and facts
- Thread-safe concurrent access
- Automatic learning from conversations

## Quick Start <a name="quickstart"></a>

### Prerequisites

- Python 3.10 or higher
- Windows OS (Linux + Mac support soon)
- 12GB+ usable RAM
- 20GB+ usable storage
- [Ollama](https://ollama.com) installed

### Installation

**1. Install AI models**

```bash
ollama pull gemma2:2b
ollama pull gpt-oss:120b
ollama pull nemotron-3-nano
ollama pull functiongemma:latest
ollama pull nomic-embed-text:latest
```

**2. Run**

```bash
# CLI mode (recommended for first use)
python main.py --cli

# Voice mode
python main.py
```

## Architecture <a name="architecture"></a>

```
┌─────────────────────────────────────────────┐
│              SENA CORE                      │
├─────────────────────────────────────────────┤
│  Intent Router (FunctionGemma)              │
│    ↓                                        │
│  LLM Manager                                │
│    ├─ Fast (Gemma2:2b)                      │
│    ├─ Critical (GPT-OSS:120b)               │
│    └─ Code (Nemotron-3-nano)                |
│                                             │
│  Memory System (mem0)                       │
│    ├─ Short-term (session context)          │
│    └─ Long-term (persistent storage)        │
│                                             │
│  Extension Manager                          │
│    ├─ Core extensions                       │
│    ├─ Auto-generated extensions             │
│    └─ Security sandbox                      │
└─────────────────────────────────────────────┘
```

### How It Works

1. **Input received** → Intent router analyzes using FunctionGemma
2. **Route decision** → Determines which LLM and extension to use
3. **Execute** → Runs appropriate handler or generates new extension
4. **Learn** → Extracts insights and stores in persistent memory
5. **Respond** → Returns result via voice or text

## Creating Extensions

Extensions are Python modules with an `execute` function:

```python
# extensions/user/my_extension.py

VERSION = "1.0.0"

METADATA = {
    'name': 'my_extension',
    'description': 'Brief description',
    'parameters': {
        'param1': 'Parameter description'
    }
}

def execute(user_input: str, context: list, **kwargs) -> str:
    """Extension logic"""
    result = # your code here
    return result
```

Place in `extensions/user/` and restart Sena.

## Configuration

Edit `config/settings.yaml`:

```yaml
llm:
  model_1:
    name: "gemma2:2b"
  model_2:
    name: "gpt-oss:120b"
  model_3:
    name: "nemotron-3-nano"
  intent_router:
    name: "functiongemma:latest"

memory:
  database_path: "memory/sena.db"
  context_limit: 10

extensions:
  max_generation_attempts: 3
```

### Common Issues

**Model not found error**
```bash
ollama pull [model-name]
```

**Out of memory error**
- Close other applications
- Use smaller models
- Check for unquantized versions

**Intent parsing error**
- Ensure all AI models mentioned in your config file are downloaded properly
- Verify config has `intent_router` section

## Development

### Testing Components
```bash
python test_sena.py llm      # Test LLM manager
python test_sena.py ext      # Test extensions
python test_sena.py db       # Test database
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Roadmap

- Mem0 integration for advanced memory
- React management dashboard
- Multi-platform support (Linux, macOS)
- Voice emotion detection
- Cloud sync capabilities

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

Inspired by Maid-chan from *Sakurasou no Pet na Kanojo*. Built with [Ollama](https://ollama.com) and memory concepts from [Mem0](https://mem0.ai).

---

<p align="center">
  <strong>Built with ❤️ by kura</strong>
</p>