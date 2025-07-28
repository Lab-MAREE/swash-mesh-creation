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
- **src/mesh.py**: Mesh generation using gmsh with adaptive refinement near shorelines and gauges
- **src/swash.py**: SWASH file handling including bathymetry parsing and INPUT file modification
- **src/utils/**: Plotting utilities for visualization with plotly

### Key Technical Details
- Mesh refinement uses distance fields from shoreline boundaries and specified gauge positions
- Exports to Triangle format (.node, .ele, .edge files) for SWASH compatibility
- Boundary numbering convention: West=1, North=2, East=3, South=4
- Bathymetry interpolation to mesh nodes using scipy.interpolate.RBFInterpolator
- Automatic detection of breakwaters from bathymetry gradients

## Code Style

- Black formatting with 79 character line length
- isort for import sorting with black profile
- Python 3.13 target
- pytest timeout set to 60 seconds
- Warnings filtered for DeprecationWarning, FutureWarning, UserWarning

## Development Workflow

- Always run code quality tools (`black`, `isort`, `ruff`, `ty check`) after modifying files
- Ensure strings and docstrings are split to respect the 79 character line length maximum
- Test coverage should be maintained for new functionality

## Key Dependencies

- **gmsh**: Core mesh generation library for creating unstructured meshes from bathymetry data
- **numpy**: Numerical operations for bathymetry and coordinate handling
- **typer**: Modern CLI framework providing the command interface
- **plotly**: Visualization of bathymetry, gauges, and mesh structures
- **scipy**: Interpolation utilities for mapping bathymetry to mesh nodes

## Testing Principles

- Never mock anything. Always use simple reusable fixtures.
- Test files follow the same structure as source files in tests/ directory
- Integration tests should use the examples/ directory data