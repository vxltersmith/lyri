# Contributing to LYRI

We welcome contributions to LYRI! Here's how you can help improve the project:

## Ways to Contribute

1. **Bug Reports**: Report issues you encounter while using LYRI
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Submit pull requests with bug fixes or new features
4. **Documentation**: Improve or add documentation
5. **Examples**: Contribute example configurations or workflows
6. **Testing**: Help test new features and report results

## Getting Started

### Setup

1. Fork the repository

2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/lyri.git
   cd lyri
   git remote add upstream https://github.com/anomalyco/lyri.git
   ```

3. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

### Development Workflow

1. Create a new branch for your changes:

   ```bash
   git checkout -b your-feature-branch
   ```

2. Make your changes

3. Run tests and linting:

   ```bash
   pytest tests/ -v
   ruff check .
   black lyri/
   mypy lyri/ --ignore-missing-imports
   ```

4. Commit your changes:

   ```bash
   git commit -m "Your descriptive commit message"
   ```

5. Push to your fork:

   ```bash
   git push origin your-feature-branch
   ```

6. Open a Pull Request on the main repository

## Code Style Guide

- Follow PEP 8 guidelines
- Use type hints for all function parameters and return values
- Use black for formatting
- Use ruff for linting
- Keep lines to 88 characters or less
- Use clear, descriptive variable and function names

## Testing

LYRI uses pytest for testing. When you contribute code, please:

1. Add tests for new functionality
2. Ensure existing tests still pass
3. Test on multiple operating systems if possible

Test files should be placed in the `tests/` directory with naming pattern `test_*.py`

## Documentation

Documentation is vital for this project. Please update documentation when you:

- Add new features
- Fix bugs
- Change API behavior
- Deprecate functionality

Documentation updates should include:

- README.md additions/changes
- AGENTS.md updates
- Code comments explaining complex logic
- Examples in the examples/ directory

## Communication

We use GitHub Issues for tracking bugs and feature requests. For more casual
communication, use [GitHub Discussions](https://github.com/vxltersmith/lyri/discussions).

## Commit Message Guidelines

Write clear, concise commit messages following these rules:

1. Separate subject from body with a blank line
2. Limit subject line to 50 characters or less
3. Use imperative mood in subject line ("Add" not "Added")
4. Wrap body at 72 characters
5. Explain what and why you changed, not just what you changed

Example:

```text
Fix audio processing hang on empty input

When input file is empty, the audio processor would hang
indefinitely. This change adds a validation check at the
beginning of processing to detect empty files and raise
a clear error message.
```

## Review Process

All contributions must be reviewed by at least one maintainer before being
merged. Review process typically includes:

1. Code quality review
2. Testing validation
3. Documentation review
4. Architecture and design considerations

## Maintainers

Current maintainers:

- @anomalyco (Main maintainer)

## Thank You

Thank you for contributing to LYRI! Your work helps make music video
generation accessible to everyone.
