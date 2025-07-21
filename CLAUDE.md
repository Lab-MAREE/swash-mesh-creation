# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This package transforms SWASH input files from cartesian coordinates to unstructured meshes using gmsh. It allows specification of points of interest to increase resolution near important areas.

## Development Environment

This project uses Python 3.13+ with uv for dependency management.

### Installation
```bash
uv sync --group dev
```

### Common Commands

**Testing:**
```bash
uv run pytest
uv run pytest -v  # verbose output
uv run pytest tests/path/to/specific_test.py  # single test file
```

**Code Quality:**
```bash
uv run black .  # format code
uv run isort .  # sort imports  
uv run ty check  # type checker
uv run ruff check  # linting
```

**Coverage:**
```bash
uv run pytest --cov=src
```

**Running CLI:**
```bash
uv run swash-mesh  # or uv run sm for short
```

## Code Architecture

The package follows a clean separation between CLI interface and core functionality:

- **src/cli.py**: Typer-based CLI with `create`/`c` and `apply`/`a` commands for mesh creation and application
- **src/main.py**: Core business logic with `create_mesh()` and `apply_mesh()` functions
- **src/__init__.py**: Package interface exposing main functions
- **examples/**: Sample SWASH configurations including 1D wave channel setup

### Current Implementation Status
- CLI framework complete with proper argument handling and help text
- Core functions implemented with file validation but mesh generation logic pending
- Ready for gmsh integration and SWASH file parsing implementation

## Code Style

- Black formatting with 79 character line length
- isort for import sorting with black profile
- Python 3.13 target
- pytest timeout set to 60 seconds
- Warnings filtered for DeprecationWarning, FutureWarning, UserWarning

## Development Workflow

- Always run code quality tools (`black`, `isort`, `ruff`, `ty check`) after modifying files
- Ensure strings and docstrings are split to respect the 79 character line length maximum
- No test suite exists yet - tests should be created in `tests/` directory following pytest conventions

## Key Dependencies

- **gmsh**: Core mesh generation library for creating unstructured meshes from bathymetry data
- **typer**: Modern CLI framework providing the command interface

## Testing Principles

- Never mock anything. Always use simple reusable fixtures.