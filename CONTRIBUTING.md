# Contributing to Sena

Thank you for your interest in contributing! This document provides guidelines for contributing to the Sena project.

## Code of Conduct

- Be respectful and inclusive
- Give credit where due
- Report issues responsibly
- Focus on the code, not the person

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Sena.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make changes and commit: `git commit -am "Add feature"`
5. Push to your fork: `git push origin feature/your-feature`
6. Open a Pull Request

## Development Standards

### Python Code

- Use Python 3.10+
- Follow PEP 8 style guide
- Add type hints where possible
- Write docstrings for functions
- Add tests for new features

```python
async def my_function(param: str) -> dict[str, str]:
    """
    Brief description of what the function does.
    
    Args:
        param: Description of parameter
    
    Returns:
        Description of return value
    """
    pass
```

### TypeScript/React

- Use TypeScript 5.5+
- Follow React best practices
- Use dark theme colors (slate-950, purple-500)
- Use lucide-react icons (no emojis)
- Add component prop interfaces

```typescript
interface MyComponentProps {
  title: string
  onClose: () => void
}

export function MyComponent({ title, onClose }: MyComponentProps) {
  return (
    <div className="bg-slate-950 text-slate-50">
      {title}
    </div>
  )
}
```

## Testing

Add tests for new features:

```bash
pytest src/tests/test_feature.py -v
```

All tests must pass before PR is accepted.

## Commit Messages

- Use clear, descriptive messages
- Reference issues: `Fix #123`
- Use imperative mood: "Add feature" not "Added feature"

Examples:
```
Add memory persistence layer
Fix bug in extension loader (#45)
Update documentation for API routes
```

## Pull Request Process

1. **One feature per PR** - Keep PRs focused
2. **Update documentation** - If adding features, update docs
3. **Add tests** - Include test coverage
4. **Link issues** - Reference related issues
5. **Be descriptive** - Explain what and why
6. **Be patient** - Reviews take time

## Areas for Contribution

### High Priority
- Bug fixes and stability improvements
- Documentation improvements
- Test coverage expansion
- Performance optimizations

### Medium Priority
- New extensions
- UI/UX improvements
- Additional language model support
- Platform support (macOS, Linux testing)

### Lower Priority
- Minor refactoring
- Code style improvements
- Internal tool optimization

## Extension Development

Want to create a new extension? See [EXTENSIONS.md](docs/EXTENSIONS.md) for the development guide.

## Documentation

- Update README.md for user-facing changes
- Update DEVELOPER.md for developer-facing changes
- Add inline comments for complex logic
- Update CHANGELOG.md before release

## Questions?

- Open a Discussion: [GitHub Discussions](https://github.com/kura120/Sena/discussions)
- Ask in Issues: [GitHub Issues](https://github.com/kura120/Sena/issues)
- Email: hello@sena-ai.dev

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in documentation

Thank you for contributing to Sena! 🚀
