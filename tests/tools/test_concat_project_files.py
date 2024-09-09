import os
import pytest
from unittest.mock import mock_open, patch, MagicMock, call

from tools.concat_project_files import (
    clean_markdown,
    decode_filename,
    parse_gitignore,
    should_ignore_file,
    concat_files
)

# Test for clean_markdown function
def test_clean_markdown():
    input_content = """
    # Title
    [Link](http://example.com)
    ![Image](http://example.com/image.jpg)
    **Bold Text**
    *Italic Text*
    - List item
    `inline code`
    ```
    block code
    ```
    """
    expected_output = "Title\nhttp://example.com\nBold Text\nItalic Text\nList item\ninline code"

    # Clean the markdown content
    cleaned_content = clean_markdown(input_content)

    # Verify that the cleaned output matches the expected output
    assert cleaned_content == expected_output.strip()


# Test for decode_filename function
def test_decode_filename():
    encoded_filename = "file%20with%20spaces.txt"
    decoded_filename = "file with spaces.txt"
    assert decode_filename(encoded_filename) == decoded_filename

# Test for parse_gitignore function
@patch("builtins.open", new_callable=mock_open, read_data="*.pyc\n.DS_Store")
@patch("os.path.exists", return_value=True)
def test_parse_gitignore(mock_exists, mock_file):
    ignore_patterns = parse_gitignore("/mocked/path")
    assert ignore_patterns == ["*.pyc", ".DS_Store"]


# Test for should_ignore_file function
def test_should_ignore_file():
    ignore_patterns = ["*.pyc", "__pycache__/", ".git/*"]

    # Matching patterns
    assert should_ignore_file("file.pyc", ignore_patterns) is True
    assert should_ignore_file("src/__pycache__/file.pyc", ignore_patterns) is True
    assert should_ignore_file(".git/config", ignore_patterns) is True

    # Non-matching patterns
    assert should_ignore_file("file.py", ignore_patterns) is False

# Test for concat_files function
@patch("os.walk")
@patch("builtins.open", new_callable=mock_open, read_data="This is the content of the file.")
def test_concat_files(mock_open, mock_walk):
    # Simulate os.walk to walk through files in a directory
    mock_walk.return_value = [
        ("/mocked/path", ["dir1"], ["file1.py", "file2.md", "file3.js"]),
    ]

    # Use concat_files with the simulated arguments
    concat_files(
        directory="/mocked/path",
        output_file="output.txt",
        exclude_empty=False,
        bypass_dirs=None,
        file_types=[".py", ".md"],
        ignore_patterns_custom=None,
        use_gitignore=False
    )

    # Collect expected write calls based on the logic of concat_files
    expected_calls = [
        call('## Path: file1.py\n'),
        call('## Filename: file1.py\n\n'),
        call('This is the content of the file.'),
        call('\n\n'),
        call('## Path: file2.md\n'),
        call('## Filename: file2.md\n\n'),
        call('This is the content of the file.'),
        call('\n\n'),
    ]

    # Check that each expected call matches the actual write calls
    mock_open().write.assert_has_calls(expected_calls, any_order=False)

@patch("os.walk")
@patch("builtins.open", new_callable=mock_open)
def test_concat_files_exclude_empty(mock_open, mock_walk):
    mock_walk.return_value = [
        ("/mocked/path", [], ["file1.py", "file2.py"]),
    ]
    mock_open.return_value.__enter__.return_value.read.side_effect = ["", "Content"]

    concat_files(
        directory="/mocked/path",
        output_file="output.txt",
        exclude_empty=True,
        bypass_dirs=None,
        file_types=[".py"],
        ignore_patterns_custom=None,
        use_gitignore=False
    )

    expected_calls = [
        call('## Path: file2.py\n'),
        call('## Filename: file2.py\n\n'),
        call('Content'),
        call('\n\n'),
    ]

    mock_open().write.assert_has_calls(expected_calls, any_order=False)

@patch("os.walk")
@patch("builtins.open", new_callable=mock_open, read_data="Content")
def test_concat_files_bypass_dirs(mock_open, mock_walk):
    mock_walk.return_value = [
        ("/mocked/path", ["dir1", "dir2"], ["file1.py"]),
        ("/mocked/path/dir1", [], ["file2.py"]),
        ("/mocked/path/dir2", [], ["file3.py"]),
    ]

    concat_files(
        directory="/mocked/path",
        output_file="output.txt",
        exclude_empty=False,
        bypass_dirs=["dir1"],
        file_types=[".py"],
        ignore_patterns_custom=None,
        use_gitignore=False
    )

    expected_calls = [
        call('## Path: file1.py\n'),
        call('## Filename: file1.py\n\n'),
        call('Content'),
        call('\n\n'),
        call(f'## Path: dir2{os.sep}file3.py\n'),
        call('## Filename: file3.py\n\n'),
        call('Content'),
        call('\n\n'),
    ]

    mock_open().write.assert_has_calls(expected_calls, any_order=False)

@patch("os.walk")
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists", return_value=True)
def test_concat_files_use_gitignore(mock_exists, mock_open, mock_walk):
    mock_walk.return_value = [
        ("/mocked/path", [], ["file1.py", "file2.py", "file3.pyc"]),
    ]
    
    # Create a mock file object
    mock_file = mock_open.return_value.__enter__.return_value
    
    # Set up the read method to return different content for each call
    mock_file.read.side_effect = [
        "*.pyc\n",  # .gitignore content
        "Content1",  # file1.py content
        "Content2",  # file2.py content
    ]

    concat_files(
        directory="/mocked/path",
        output_file="output.txt",
        exclude_empty=False,
        bypass_dirs=None,
        file_types=[".py"],
        ignore_patterns_custom=None,
        use_gitignore=True
    )

    # Check that open was called for .gitignore and the two .py files
    mock_open.assert_any_call(os.path.join("/mocked/path", ".gitignore"), "r", encoding="utf-8")
    mock_open.assert_any_call(os.path.join("/mocked/path", "file1.py"), "r", encoding="utf-8")
    mock_open.assert_any_call(os.path.join("/mocked/path", "file2.py"), "r", encoding="utf-8")

@patch("os.walk")
@patch("builtins.open", new_callable=mock_open, read_data="Content")
def test_concat_files_ignore_patterns_custom(mock_open, mock_walk):
    mock_walk.return_value = [
        ("/mocked/path", [], ["file1.py", "file2.txt", "file3.pyc"]),
    ]

    concat_files(
        directory="/mocked/path",
        output_file="output.txt",
        exclude_empty=False,
        bypass_dirs=None,
        file_types=[".py", ".txt"],
        ignore_patterns_custom=["*.pyc", "file2.*"],
        use_gitignore=False
    )

    expected_calls = [
        call('## Path: file1.py\n'),
        call('## Filename: file1.py\n\n'),
        call('Content'),
        call('\n\n'),
    ]

    mock_open().write.assert_has_calls(expected_calls, any_order=False)

@patch("os.walk")
@patch("builtins.open", new_callable=mock_open)
def test_concat_files_read_error(mock_open, mock_walk):
    mock_walk.return_value = [
        ("/mocked/path", [], ["file1.py", "file2.py"]),
    ]
    
    mock_open.return_value.__enter__.return_value.read.side_effect = [
        UnicodeDecodeError("utf-8", b"", 0, 1, "Invalid start byte"),
        "Content2"
    ]

    concat_files(
        directory="/mocked/path",
        output_file="output.txt",
        exclude_empty=False,
        bypass_dirs=None,
        file_types=[".py"],
        ignore_patterns_custom=None,
        use_gitignore=False
    )

    expected_calls = [
        call('## Path: file2.py\n'),
        call('## Filename: file2.py\n\n'),
        call('Content2'),
        call('\n\n'),
    ]

    mock_open().write.assert_has_calls(expected_calls, any_order=False)