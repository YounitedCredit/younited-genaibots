import os
import re
import urllib.parse
import argparse
import fnmatch
import logging
import colorama
from colorama import Fore, Style
from pathlib import Path

help_description = """
Project File Concatenator Script with .gitignore Support, Custom Exclude Patterns, and Directory Bypass

This script processes a directory (e.g., a cloned GitHub project) and concatenates files while excluding those listed in the .gitignore file, or via custom patterns.
It cleans the content of markdown or code files and provides metadata such as the full file path for easier usage with language models.

Usage:
  python concat_project_files.py --input <input_path> --output <output_file> [--exclude_empty] [--bypass_dirs <dir1> <dir2> ...] [--include_files <ext1> <ext2> ...] [--ignore-patterns <pattern1> <pattern2> ...] [--use-gitignore]

Arguments:
  --input              : Path to the project directory (required).
                         This should be the root of your project directory (e.g., a cloned GitHub repository).
                         Example: --input /path/to/project

  --output             : Path to the output file where concatenated content will be stored (required).
                         Example: --output /path/to/output.txt

  --exclude_empty      : Optional flag to exclude empty files from concatenation.
                         Example: --exclude_empty

  --bypass_dirs        : Optional list of directories to bypass during concatenation.
                         Example: --bypass_dirs ./tests ./examples
                         This will skip the directories "tests" and "examples" during concatenation.

  --include_files      : Optional list of file extensions to include (e.g., .md, .py, .js).
                         Example: --include_files .md .py
                         This will only include markdown and Python files in the output.

  --ignore-patterns    : Optional list of custom ignore patterns (e.g., __pycache__, .* for hidden files).
                         Example: --ignore-patterns "__pycache__" ".*"
                         This will ignore all `__pycache__` directories and hidden files (those starting with a dot).

  --use-gitignore      : Optional flag to use the .gitignore file as an additional filter.
                         If present, the script will respect the patterns listed in the `.gitignore` file.
                         Example: --use-gitignore

Examples:

1. Basic usage (concatenates all relevant files from the input directory):
   python concat_project_files.py --input /path/to/project --output output.txt

2. Exclude empty files from concatenation:
   python concat_project_files.py --input /path/to/project --output output.txt --exclude_empty

3. Bypass specific directories (skipping "tests" and "docs"):
   python concat_project_files.py --input /path/to/project --output output.txt --bypass_dirs ./tests ./docs

4. Include only markdown and Python files:
   python concat_project_files.py --input /path/to/project --output output.txt --include_files .md .py

5. Use custom ignore patterns (ignore __pycache__ and hidden files):
   python concat_project_files.py --input /path/to/project --output output.txt --ignore-patterns "__pycache__" ".*"

6. Use .gitignore as filter:
   python concat_project_files.py --input /path/to/project --output output.txt --use-gitignore

7. Combine multiple arguments (use .gitignore, exclude empty files, and bypass specific directories):
   python concat_project_files.py --input /path/to/project --output output.txt --exclude_empty --use-gitignore --bypass_dirs ./tests ./docs --include_files .md .py
"""

# Setup logging with custom colored output
colorama.init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    format_str = '%(asctime)s - %(levelname)s - %(message)s'

    FORMATS = {
        logging.DEBUG: Style.DIM + format_str + Style.RESET_ALL,
        logging.INFO: format_str,
        logging.WARNING: Fore.YELLOW + format_str + Style.RESET_ALL,
        logging.ERROR: Fore.RED + format_str + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + format_str + Style.RESET_ALL
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Log everything for debugging

# File handler (logs to file without color)
file_handler = logging.FileHandler('concatenation_process.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
# Stream handler (colored output to console)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(ColoredFormatter())
logger.addHandler(stream_handler)

# Clean markdown or code content
def clean_markdown(content):
    """Remove markdown-specific syntax and clean content."""
    content = re.sub(r'^\s*#+\s', '', content, flags=re.MULTILINE)  # Remove titles
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # Remove links
    content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)  # Remove images
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold
    content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italics
    content = re.sub(r'^\s*[-*+]\s+', '', content, flags=re.MULTILINE)  # Remove lists
    content = re.sub(r'`(.*?)`', r'\1', content)  # Remove inline code
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)  # Remove code blocks
    return content

def decode_filename(filename):
    """Decode any URL-encoded characters in a filename."""
    return urllib.parse.unquote(filename)

def parse_gitignore(directory):
    """Read the .gitignore file and return a list of patterns to ignore."""
    gitignore_path = os.path.join(directory, '.gitignore')
    ignore_patterns = []
    if os.path.exists(gitignore_path):
        logger.info(f"Found .gitignore file: {gitignore_path}")
        with open(gitignore_path, 'r', encoding='utf-8') as gitignore:
            for line in gitignore:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignore_patterns.append(line)
                    logger.debug(f"Adding .gitignore pattern: {line}")
    else:
        logger.info("No .gitignore file found.")
    return ignore_patterns

def should_ignore_file(filepath, ignore_patterns):
    """Check if a file matches a .gitignore pattern."""
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(filepath, f'*/{pattern}'):
            logger.debug(f"File {filepath} matches ignore pattern: {pattern}")
            return True
    return False

def concat_files(directory, output_file, exclude_empty, bypass_dirs, file_types, ignore_patterns_custom, use_gitignore):
    """Concatenate files from a directory into a single output file, excluding files based on .gitignore, empty files, and bypassed directories."""
    
    # Initialize bypass_dirs as an empty list if it's None
    if bypass_dirs is None:
        bypass_dirs = []
    
    # Convert file_types to a tuple for endswith
    if isinstance(file_types, list):
        file_types = tuple(file_types)
    
    ignore_patterns = []
    
    # Add .gitignore patterns if --use-gitignore is provided
    if use_gitignore:
        ignore_patterns.extend(parse_gitignore(directory))
        logger.info(f"Using .gitignore patterns.")

    # Add custom ignore patterns from the command line
    if ignore_patterns_custom:
        ignore_patterns.extend(ignore_patterns_custom)
        logger.info(f"Adding custom ignore patterns: {ignore_patterns_custom}")

    # Add manually common virtual environment directories (e.g., .venv, venv) and __pycache__
    ignore_patterns.extend(['.venv/', 'venv/', '*/.venv/*', '*/venv/*', '__pycache__/', '*/__pycache__/*'])

    # Add bypass directories to ignore patterns
    if bypass_dirs:
        for bypass_dir in bypass_dirs:
            ignore_patterns.append(os.path.join(bypass_dir, '*'))
            logger.info(f"Adding bypass directory: {bypass_dir}")

    file_count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(directory):
            # Apply ignore patterns to directories
            dirs[:] = [d for d in dirs if not should_ignore_file(os.path.join(root, d), ignore_patterns)]

            # Check if the current directory is in bypass_dirs
            if any(fnmatch.fnmatch(root, os.path.join(directory, d)) for d in bypass_dirs):
                logger.info(f"Bypassing directory: {root}")
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)

                # Exclude hidden files, files in .gitignore, and non-relevant files
                if file.startswith('.') or should_ignore_file(relative_path, ignore_patterns):
                    logger.debug(f"Skipping file: {relative_path}")
                    continue
                
                # Check if the file has an extension matching file_types (now a tuple)
                if not file.endswith(file_types):  
                    logger.debug(f"Skipping non-relevant file type: {relative_path}")
                    continue

                # Try reading file content and handle encoding issues
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read().strip()  # Strip whitespace
                except (UnicodeDecodeError, OSError) as e:
                    logger.warning(f"Skipping file due to encoding issue or read error: {relative_path}. Error: {e}")
                    continue

                # Skip empty files if exclude_empty is set
                if exclude_empty and not content:
                    logger.debug(f"Skipping empty file: {relative_path}")
                    continue

                decoded_filename = decode_filename(file)
                outfile.write(f"## Path: {relative_path}\n")
                outfile.write(f"## Filename: {decoded_filename}\n\n")
                cleaned_content = clean_markdown(content)
                outfile.write(cleaned_content)
                outfile.write("\n\n")
                file_count += 1
                logger.info(f"Processed file: {relative_path}")

    logger.info(f"Concatenation complete. Processed {file_count} files. Output written to {output_file}.")

# Parse command-line arguments
parser = argparse.ArgumentParser(description=help_description, formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('--input', required=True, help='Path to the project directory (required)')
parser.add_argument('--output', required=True, help='Path to the output file (required)')
parser.add_argument('--exclude_empty', action='store_true', help='Exclude empty files from concatenation')
parser.add_argument('--bypass_dirs', nargs='*', help='List of directories to bypass (optional)')
parser.add_argument('--include_files', nargs='*', help='List of file extensions to include (e.g., .md .py .js)')
parser.add_argument('--ignore-patterns', nargs='*', help='List of custom ignore patterns (e.g., __pycache__, .* for hidden files)')
parser.add_argument('--use-gitignore', action='store_true', help='Use the .gitignore file as an additional filter')

args = parser.parse_args()

# Run the concatenation function with the provided arguments
concat_files(
    args.input,
    args.output,
    args.exclude_empty,
    args.bypass_dirs,
    args.include_files or ['.md', '.py', '.js', '.java', '.cpp'],
    args.ignore_patterns,
    args.use_gitignore
)
