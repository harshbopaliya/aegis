# Contributing to Aegis

First off, thank you for considering contributing to the Aegis! It's people like you that make this such a great tool.

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps which reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include screenshots and animated GIFs if possible**
- **Include your environment details**: OS, Python version, FastAPI version, etc.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and expected behavior**
- **Explain why this enhancement would be useful**

### Pull Requests

- Fill in the required template
- Follow the Python styleguides (PEP 8, Black formatter)
- Include appropriate test cases
- End all files with a newline
- Update documentation as needed
- Reference relevant issue numbers

## Development Setup

### Fork and Clone

```bash
# Clone the main repository
git clone https://github.com/harshbopaliya/aegis.git
cd aegis

# OR: Fork the repository on GitHub and clone your fork
git clone https://github.com/YOUR_USERNAME/aegis.git
cd aegis

# Add upstream remote (if you forked)
git remote add upstream https://github.com/harshbopaliya/aegis.git
```

### Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_gateway.py -v

# Run with markers
pytest -m "not slow" -v
```

### Code Quality

```bash
# Format code
make format
# or
black aegis/ tests/

# Lint code
make lint
# or
flake8 aegis/ tests/

# Type checking
make typecheck
# or
mypy aegis/

# Security scanning
bandit -r aegis/

# All checks
make quality
```

### Local Development Server

```bash
# Start with hot reload
make run

# or manually
aegis serve --debug
```

### Docker Development

```bash
# Build development image
docker build -f Dockerfile -t aegis:dev .

# Run container
docker run -p 8000:8000 \
  -e ASG_ENVIRONMENT=development \
  -e ASG_DEBUG=true \
  aegis:dev

# Run with docker-compose
docker-compose -f docker-compose.yml up -d
```

## Styleguides

### Python Code Style

This project uses **Black** for code formatting and follows **PEP 8**. Configuration is in `pyproject.toml`.

```bash
# Format all Python files
black aegis/ tests/

# Check formatting without changing files
black --check aegis/ tests/
```

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Format:
```
<type>: <subject>

<body>

Closes #<issue_number>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

Example:
```
feat: add risk scoring module for policy evaluation

Implement a new risk scoring system that evaluates actions
on a 0-100 scale based on resource type and operation verb.

Closes #42
```

### Documentation Style

- Use Markdown for all documentation
- Include code examples where relevant
- Keep sections concise but complete
- Use clear, beginner-friendly language
- Update documentation with code changes

## Testing Guidelines

### Writing Tests

```python
# tests/test_example.py
import pytest
from aegis.core.db import connect

class TestExample:
    """Test Example service."""
    
    @pytest.fixture
    def example_service(self):
        """Provide Example service instance."""
        return Example()
    
    def test_something_works(self, example_service):
        """Test that something works correctly."""
        result = example_service.do_something()
        assert result is not None
```

### Test Coverage

- Aim for 80%+ code coverage
- Test both happy path and error cases
- Use descriptive test names
- Include fixtures for common setups

```bash
# Check coverage
pytest --cov=app --cov-report=term-missing
```

## Module Contribution Guidelines

Each module has specific purposes. When contributing, ensure alignment:

| Module | Purpose | Test Coverage |
|--------|---------|---------------|
| **policy_engine** | Policy validation and enforcement | 85%+ |
| **risk_scoring** | Risk assessment 0-100 | 85%+ |
| **execution** | Safe action execution | 90%+ |
| **human_loop** | Approval workflow | 85%+ |
| **backup_recovery** | Data protection | 80%+ |
| **observability** | Audit logging | 85%+ |
| **token_scoping** | RBAC enforcement | 85%+ |
| **sandbox** | Safe simulation | 80%+ |

## Documentation Contributions

Documentation contributions are just as valuable as code! You can help by:

- Improving existing documentation
- Fixing typos and grammatical errors
- Adding examples and use cases
- Translating documentation to other languages
- Creating tutorials and guides

## Security Vulnerabilities

Please DO NOT create public issues for security vulnerabilities. Instead, please email security@yourdomain.com with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

## Community

- **Discussions**: GitHub Discussions for feature ideas and Q&A
- **Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions
- **Slack/Discord**: [Add community chat link if applicable]

## Recognition

Contributors will be recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md) file
- Release notes for their contributions
- GitHub's contributor list

## Questions?

- 📚 Check the [README.md](README.md)
- 📖 Read [PRODUCTION_README.md](PRODUCTION_README.md)
- 🐛 Search [existing issues](https://github.com/harshbopaliya/aegis/issues)
- 💬 Start a [discussion](https://github.com/harshbopaliya/aegis/discussions)

Thank you for contributing to making AI systems safer! 🔒

---

**Happy Contributing!**
