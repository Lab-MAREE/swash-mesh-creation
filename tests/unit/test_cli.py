from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from typer import Typer
from typer.testing import CliRunner

from src.cli import _init_cli, run_cli


def test_cli(runner: CliRunner, cli: Typer) -> None:
    resp = runner.invoke(cli, ["-h"])
    assert resp.exit_code == 0
    assert "Usage" in resp.output

    resp = runner.invoke(cli, ["--help"])
    assert resp.exit_code == 0
    assert "Usage" in resp.output


def test_init_cli() -> None:
    cli = _init_cli()
    assert isinstance(cli, Typer)


def test_run_cli(mocker: MockerFixture) -> None:
    init_cli = mocker.patch("src.cli._init_cli")
    run_cli()
    init_cli.assert_called_once()


@pytest.mark.parametrize("command", ["create", "c"])
def test_create_mesh_command(
    runner: CliRunner,
    cli: Typer,
    tmp_path: Path,
    command: str,
) -> None:
    # Create a test bathymetry file
    bathymetry_file = tmp_path / "bathymetry.txt"
    bathymetry_file.write_text("test data")

    # Test the command - should call main.create_mesh
    resp = runner.invoke(cli, [command, str(bathymetry_file)])
    assert resp.exit_code == 0

    # Test with non-existent file
    non_existent_file = tmp_path / "non_existent.txt"

    resp = runner.invoke(cli, [command, str(non_existent_file)])
    assert resp.exit_code != 0


@pytest.mark.parametrize("command", ["apply", "a"])
def test_apply_mesh_command(
    runner: CliRunner,
    cli: Typer,
    tmp_path: Path,
    command: str,
) -> None:
    # Create test files
    mesh_file = tmp_path / "mesh.msh"
    mesh_file.write_text("mesh data")
    input_file_1 = tmp_path / "INPUT"
    input_file_1.write_text("input data 1")
    input_file_2 = tmp_path / "gauge.txt"
    input_file_2.write_text("gauge data")

    # Test without in_place flag
    resp = runner.invoke(
        cli, [command, str(mesh_file), str(input_file_1), str(input_file_2)]
    )
    assert resp.exit_code == 0

    # Test with in_place flag
    resp = runner.invoke(
        cli,
        [
            command,
            str(mesh_file),
            str(input_file_1),
            str(input_file_2),
            "--in-place",
        ],
    )
    assert resp.exit_code == 0

    # Test with non-existent files
    non_existent_mesh = tmp_path / "non_existent.msh"
    non_existent_input = tmp_path / "non_existent_input.txt"

    resp = runner.invoke(
        cli, [command, str(non_existent_mesh), str(non_existent_input)]
    )
    assert resp.exit_code != 0
