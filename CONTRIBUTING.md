# 🤝 Contributing to HeySeen

Thank you for your interest in contributing to HeySeen! We welcome contributions from the community to help make this the best open-source PDF-to-LaTeX converter for Apple Silicon.

---

## 🎯 How Can I Contribute?

### 🐛 Reporting Bugs

Found a bug? Please help us fix it!

1. **Check existing issues** first to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Your environment (macOS version, Python version, RAM)
   - Sample PDF file (if possible and non-confidential)
   - Error logs from `server_data/server.log`

### 💡 Suggesting Features

Have an idea? We'd love to hear it!

1. **Check discussions** to see if it's already proposed
2. **Open a feature request** with:
   - Clear use case and benefits
   - Expected behavior
   - Potential implementation approach (optional)

### 🔧 Contributing Code

#### Setup Development Environment

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/HeySeen.git
cd HeySeen

# 2. Install system dependencies
brew install poppler tesseract

# 3. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install project and dependencies
pip install -e .
pip install -r requirements.txt

# 5. Install dev tools
pip install pytest black isort mypy ruff
```

#### Development Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-123

# 2. Make your changes
# - Write code
# - Add tests
# - Update documentation

# 3. Run quality checks
black heyseen/              # Format code
isort heyseen/              # Sort imports
mypy heyseen/               # Type checking
pytest tests/               # Run tests

# 4. Commit your changes
git add .
git commit -m "feat: add amazing feature

- Detailed description
- What changed
- Why it matters"

# 5. Push and create PR
git push origin feature/your-feature-name
```

#### Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]
[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Examples:**
```
feat: add table detection to layout analyzer

fix: resolve memory leak in PDF loader

docs: update installation instructions for M3 chips

refactor: simplify TeX builder logic
```

---

## 📁 Project Structure

```
HeySeen/
├── heyseen/
│   ├── core/              # Core processing logic
│   │   ├── pdf_loader.py       # PDF → Image conversion
│   │   ├── layout_analyzer.py  # Layout detection
│   │   ├── content_extractor.py # Text/Math extraction
│   │   ├── tex_builder.py      # LaTeX generation
│   │   └── ...
│   ├── server/            # Web application
│   │   ├── app.py              # FastAPI backend
│   │   └── static/             # Frontend files
│   ├── cli/               # Command-line interface
│   └── utils/             # Utility functions
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── scripts/               # Development scripts
├── deploy/                # Deployment configs
└── docs/                  # Additional documentation
```

---

## 🧪 Testing Guidelines

### Writing Tests

```python
# tests/unit/test_pdf_loader.py
import pytest
from heyseen.core.pdf_loader import PDFLoader

def test_pdf_loader_creates_images():
    """Test that PDF loader converts pages to images."""
    loader = PDFLoader("test.pdf")
    images = loader.load_pages()
    
    assert len(images) > 0
    assert images[0].size[0] > 0  # Width
    assert images[0].size[1] > 0  # Height
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_pdf_loader.py

# Run with coverage
pytest --cov=heyseen tests/

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v
```

---

## 📝 Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use type hints where possible
- Maximum line length: 88 characters (Black default)
- Use descriptive variable names

### Example

```python
from pathlib import Path
from typing import List, Optional
from PIL import Image

def load_pdf_pages(
    pdf_path: Path,
    dpi: int = 300,
    max_pages: Optional[int] = None
) -> List[Image.Image]:
    """
    Load PDF pages as PIL Images.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for image conversion
        max_pages: Maximum number of pages to load
    
    Returns:
        List of PIL Images, one per page
    
    Raises:
        FileNotFoundError: If PDF file doesn't exist
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Implementation...
    return images
```

### Formatting Tools

```bash
# Auto-format code
black heyseen/

# Sort imports
isort heyseen/

# Lint code
ruff check heyseen/

# Type checking
mypy heyseen/
```

---

## 🔍 Pull Request Process

### Before Submitting

- ✅ All tests pass (`pytest`)
- ✅ Code is formatted (`black`, `isort`)
- ✅ Type hints added where appropriate
- ✅ Documentation updated (if needed)
- ✅ No merge conflicts with `main`

### PR Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Tests pass locally
- [ ] Code formatted with Black
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process

1. Automated checks run (tests, linting)
2. Code review by maintainers
3. Address feedback
4. Approval and merge

---

## 🌟 Areas We Need Help

### High Priority
- 📊 **Benchmark Suite**: Automated accuracy testing
- 🎨 **UI/UX Improvements**: Better web interface
- 📖 **Documentation**: Tutorials, examples, guides
- 🧪 **Test Coverage**: More unit and integration tests

### Medium Priority
- 🌐 **Internationalization**: Support for non-English PDFs
- 🔍 **Quality Metrics**: Better accuracy measurement
- ⚡ **Performance**: Optimization for large documents
- 🔌 **Plugin System**: Extensible architecture

### Good First Issues
Look for issues labeled `good-first-issue` on GitHub - these are great entry points!

---

## 💬 Community

- 💬 [GitHub Discussions](https://github.com/phucdhh/HeySeen/discussions) - Ask questions, share ideas
- 🐛 [GitHub Issues](https://github.com/phucdhh/HeySeen/issues) - Report bugs, request features
- 📧 Contact: Create a discussion thread

---

## 📄 License

By contributing to HeySeen, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Recognition

All contributors will be recognized in our README and releases. Thank you for making HeySeen better!

---

**Happy Contributing! 🎉**
