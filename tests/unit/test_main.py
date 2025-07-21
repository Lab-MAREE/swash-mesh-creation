from pathlib import Path

import pytest

from src.main import _verify_file_existence, apply_mesh, create_mesh

##########
# public #
##########


def test_create_mesh(tmp_path: Path) -> None:
    # Test with non-existent file
    non_existent_file = tmp_path / "non_existent.txt"
    with pytest.raises(FileNotFoundError):
        create_mesh(non_existent_file)

    # Create a test bathymetry file
    bathymetry_file = tmp_path / "bathymetry.txt"
    bathymetry_file.write_text("test data")

    # Test correctly works
    create_mesh(bathymetry_file)


def test_apply_mesh(tmp_path: Path) -> None:
    # Test with non-existent files
    non_existent_mesh = tmp_path / "non_existent.msh"
    non_existent_input = tmp_path / "non_existent_input.txt"
    with pytest.raises(FileNotFoundError):
        apply_mesh(non_existent_mesh, [non_existent_input])

    # Create test files
    mesh_file = tmp_path / "mesh.msh"
    mesh_file.write_text("mesh data")
    input_file_1 = tmp_path / "INPUT"
    input_file_1.write_text("input data 1")
    input_file_2 = tmp_path / "gauge.txt"
    input_file_2.write_text("gauge data")

    # Test correctly works
    apply_mesh(mesh_file, [input_file_1, input_file_2])

    # Test correctly works in-place
    apply_mesh(mesh_file, [input_file_1, input_file_2], in_place=True)


###########
# private #
###########


def test_verify_file_existence(tmp_path: Path) -> None:
    # Test with existing files
    existing_file_1 = tmp_path / "file1.txt"
    existing_file_1.write_text("content1")
    existing_file_2 = tmp_path / "file2.txt"
    existing_file_2.write_text("content2")

    # Should not raise any exception
    _verify_file_existence([existing_file_1, existing_file_2])

    # Test with non-existent files
    non_existent_file_1 = tmp_path / "missing1.txt"
    non_existent_file_2 = tmp_path / "missing2.txt"

    with pytest.raises(FileNotFoundError) as exc_info:
        _verify_file_existence([non_existent_file_1, non_existent_file_2])

    # Check error message contains file paths
    error_msg = str(exc_info.value)
    assert "don't exist" in error_msg

    # Test with mixed existing and non-existent files
    with pytest.raises(FileNotFoundError):
        _verify_file_existence([existing_file_1, non_existent_file_1])

    # Test with empty list
    _verify_file_existence([])
