import subprocess
from unittest.mock import call, patch

import pytest

from install_requirements import install_requirements


@pytest.fixture
def temp_directory(tmp_path):
    """Create a temporary directory structure for testing"""
    # Créer un répertoire de test avec une structure
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    # Créer un sous-répertoire
    sub_dir = test_dir / "subdir"
    sub_dir.mkdir()

    return test_dir

@pytest.fixture
def requirements_files(temp_directory):
    """Create test requirements.txt files"""
    # Créer un requirements.txt dans le répertoire principal
    main_req = temp_directory / "requirements.txt"
    main_req.write_text("pytest==7.3.1\nrequests==2.28.1")

    # Créer un requirements.txt dans le sous-répertoire
    sub_req = temp_directory / "subdir" / "requirements.txt"
    sub_req.write_text("pandas==1.5.3")

    return main_req, sub_req

def test_find_requirements_files(temp_directory, requirements_files):
    """Test that the function finds all requirements.txt files"""
    main_req, sub_req = requirements_files

    # Patcher os.walk pour ne retourner que nos fichiers de test
    def mock_walk(path):
        yield str(temp_directory), ['subdir'], ['requirements.txt']
        yield str(temp_directory / 'subdir'), [], ['requirements.txt']

    with patch('os.walk', mock_walk):
        with patch('subprocess.run') as mock_run:
            install_requirements()

            # Vérifier que pip install a été appelé pour chaque fichier requirements.txt
            assert mock_run.call_count == 2

            # Vérifier les appels exacts avec les chemins absolus
            expected_calls = [
                call(['pip', 'install', '-r', str(temp_directory / 'requirements.txt')], check=True),
                call(['pip', 'install', '-r', str(temp_directory / 'subdir' / 'requirements.txt')], check=True)
            ]

            mock_run.assert_has_calls(expected_calls, any_order=True)

def test_no_requirements_files(temp_directory):
    """Test behavior when no requirements.txt files are present"""
    # Patcher os.walk pour simuler un répertoire vide
    def mock_walk(path):
        yield str(temp_directory), [], []

    with patch('os.walk', mock_walk):
        with patch('subprocess.run') as mock_run:
            install_requirements()
            mock_run.assert_not_called()

def test_pip_install_error(temp_directory, requirements_files):
    """Test handling of pip install errors"""
    main_req = requirements_files[0]

    def mock_walk(path):
        yield str(temp_directory), [], ['requirements.txt']

    with patch('os.walk', mock_walk):
        with patch('subprocess.run') as mock_run:
            # Simuler une erreur lors de l'installation
            mock_run.side_effect = subprocess.CalledProcessError(1, ['pip'])

            # Vérifier que l'exception est propagée
            with pytest.raises(subprocess.CalledProcessError):
                install_requirements()

def test_permission_error(temp_directory):
    """Test handling of permission errors"""
    with patch('os.walk') as mock_walk:
        # Simuler une erreur de permission
        mock_walk.side_effect = PermissionError("Permission denied")

        # Vérifier que l'exception est propagée
        with pytest.raises(PermissionError):
            install_requirements()
