import os
import re
import sys
import logging


def merge_source_files(pdf_dict):
    """
    Merge Markdown files from source dynamically based on the calling script.

    Parameters:
    - pdf_dict: Dictionary containing paths and other metadata.

    Returns:
    - merged_source_files: Markdown files merged in order following naming conventions.
    """

    source_path = pdf_dict.get('source_path')
    logging.debug(f"merge_source_files: Source path: {source_path}")
    logging.debug(f"Contents of source path: {os.listdir(source_path)}")

    introduction_file = None
    for filename in os.listdir(source_path):
        if "introduction.md" in filename:  # Match introduction.md with or without "00-" prepended
            introduction_file = os.path.join(source_path, filename)
            logging.debug(f"Introduction file found: {introduction_file}")
            break

    if not introduction_file:
        logging.error("No 'introduction.md' file found (with or without '00-').")
        sys.exit(1)

    numbered_files = []
    resources_file = None

    for filename in os.listdir(source_path):
        file_path = os.path.join(source_path, filename)

        if "introduction.md" in filename:
            introduction_file = file_path

        elif "resources.md" in filename:  # Match resources.md with or without a number
            resources_file = file_path

        else:
            # Check for numbered lab files (e.g., 01-lab.md)
            file_pattern = re.compile(r'^\d{2}-.+\.md$')
            if file_pattern.match(filename):
                numbered_files.append(file_path)

    # Sort numbered files to determine sequence order
    numbered_files.sort()

    # Prepare the list of files to process
    files_to_process = []

    # Add introduction file first
    if introduction_file:
        files_to_process.append(introduction_file)

    # Add numbered files to the processing list
    files_to_process.extend(numbered_files)

    # Function to check if a file is already numbered
    def is_numbered_file(file_name):
        return bool(re.match(r"^\d{2}-", file_name))

    # Handle the resources file
    if resources_file:
        resources_file_basename = os.path.basename(resources_file)

        if is_numbered_file(resources_file_basename):
            # If already numbered, use it directly
            numbered_resources_file = resources_file
        else:
            # Determine the last number in the list of files
            last_number = int(numbered_files[-1].split('-')[0]) if numbered_files else 0
            new_resources_file_name = f"{last_number + 1:02d}-resources.md"
            numbered_resources_file = os.path.join(source_path, new_resources_file_name)
            logging.debug(f"Resources file will be treated as: {numbered_resources_file}")

        # Add the resources file to the processing list (using the new numbered name if needed)
        files_to_process.append(numbered_resources_file)

    if not files_to_process:
        print("No files matched the expected naming conventions.")
        return None

    # Merge the files
    merged_source_files = ""
    for file_path in files_to_process:
        # Use the actual file path for reading, not the new numbered name
        original_file_path = file_path if os.path.isfile(file_path) else resources_file
        with open(original_file_path, 'r', encoding="utf-8") as file:
            merged_source_files += file.read() + '\n'
            print(f"Reading {original_file_path}")

    return merged_source_files