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

- **src/cli.py**: Main CLI entry point using Typer framework
- The CLI is initialized but currently has no commands registered
- Uses gmsh for mesh generation (key dependency)
- Package provides two console scripts: `swash-mesh` and `sm` (shorthand)

## Code Style

- Black formatting with 79 character line length
- isort for import sorting with black profile
- Python 3.13 target
- pytest timeout set to 60 seconds
- Warnings filtered for DeprecationWarning, FutureWarning, UserWarning
