# Agent Guidelines for flask-googlestorage

This document defines project-scoped rules, coding style, development workflow, and testing practices for AI agents working on the `flask-googlestorage` project.

## Codebase Overview

`flask-googlestorage` is a Flask extension that integrates Google Cloud Storage (GCS) with local storage fallbacks.

```
flask-googlestorage/
├── .github/                 # GitHub workflows and dependabot configuration
├── docs/                    # Sphinx documentation source
├── flask_googlestorage/     # Core extension source code
│   ├── __init__.py          # Package entry point and exports
│   ├── buckets.py           # Contains bucket abstractions: Bucket, LocalBucket, and CloudBucket
│   ├── exceptions.py        # Custom exceptions
│   ├── google_storage.py    # Main GoogleStorage extension class
│   └── utils.py             # Internal helper functions
├── tests/                   # Unit test suite
├── AGENTS.md                # This rules and guidelines file
├── pyproject.toml           # PEP 518 build system and tool configuration (Ruff, uv)
├── setup.cfg                # Configuration file for bumpversion
└── tox.ini                  # Tox configuration mapping Python environments and commands
```

## Coding Standards & Style

### 1. Python Style Guide (PEP 8)

- Always write clean Python code adhering to PEP 8 standards.
- Use 4 spaces for indentation.

### 2. Line Length and Complexity

- **Line Length**: Hard limit of **100 characters** per line.
- **Complexity**: Maximum cyclomatic complexity of **10**.
- Code must pass linting without errors.

### 3. Sphinx/RST Docstrings

- Use Sphinx-style (reStructuredText) syntax for all docstrings.
- Docstrings and code styling are linted and formatted via `ruff`.

### 4. Type Annotations

- Use Python standard type hints (`typing` module) for function parameters and return values.

## Development Workflow

### 1. Branching

- Always create a new branch derived from `master` for any changes.

### 2. Running Linting and Tests

- **Tox**: Tests and linting must be run using `tox`.
- **Commands**:
  - Run linting: `uv run tox -e lint`
  - Run all tests: `uv run tox -e py310,py311,py312,py313,py314`
