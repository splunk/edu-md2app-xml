import re
import os
import sys


def merge_source_files(pdf_dict):
    """
    Merge Markdown files from source dynamically based on the calling script.

    Parameters:
    - source_path: Path to directory containing Markdown files

    Returns:
    - merged_source_files: Markdown files merged in order following naming conventions.

    Raises:
    - TODO: SWAP PRINT STATEMENT FOR ERROR HANDLING
    """

    source_path = pdf_dict.get('source_path')

    merged_source_files = str()

    introduction_file = None
    numbered_files = []
    resources_file = None

    for filename in os.listdir(source_path):
        file_path = os.path.join(source_path, filename)  # Fix: Assign file_path early

        if 'introduction.md' in filename:
            introduction_file = file_path

        elif 'resources.md' in filename:
            resources_file = file_path

        else: 
            # Check for numbered lab files (e.g., 01-lab.md)
            file_pattern = re.compile(r'^\d{2}-.+\.md$')
            if file_pattern.match(filename):
                numbered_files.append(file_path)

    files_to_process = []

    if not introduction_file: 
        intro_check = input("No 'introduction.md' found. Do you want to proceed? (y/n) ")
        if intro_check.lower() == 'n':
            sys.exit()
    
    if not numbered_files: 
        numbered_check = input("No numbered files found. Do you want to proceed? (y/n) ")
        if numbered_check.lower() == 'n':
            sys.exit()
            
    if not resources_file: 
        resource_check = input("No 'resources.md' found. Do you want to proceed? (y/n) ")
        if resource_check.lower() == 'n':
            sys.exit()

    if introduction_file:
        files_to_process.append(introduction_file)

    numbered_files.sort()  # Sort numbered files
    files_to_process.extend(numbered_files)

    if resources_file:
        files_to_process.append(resources_file)

    if not files_to_process:
        print("No files matched the expected naming conventions.")
        return None

    # Merge the files
    for file_path in files_to_process:
        with open(file_path, 'r', encoding="utf-8") as file:
            merged_source_files += file.read()  + '\n'
            print(f"Reading {file_path}")

    return merged_source_files
