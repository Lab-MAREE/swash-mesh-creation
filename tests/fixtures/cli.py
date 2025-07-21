import pytest
import typer
from typer.testing import CliRunner

from src.cli import _init_cli


@pytest.fixture(scope="session")
def cli() -> typer.Typer:
    return _init_cli()


@pytest.fixture(scope="session")
def runner() -> CliRunner:
    return CliRunner()
