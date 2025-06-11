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
        if filename.startswith("00-") and "introduction.md" in filename:
            introduction_file = os.path.join(source_path, filename)
            logging.debug(f"Introduction file found: {introduction_file}")

    if not introduction_file:
        logging.error("No '00-introduction.md' found during merge_source_files.")
        sys.exit(1)

    numbered_files = []
    resources_file = None

    for filename in os.listdir(source_path):
        file_path = os.path.join(source_path, filename)

        if filename.startswith("00-") and "introduction.md" in filename:
            introduction_file = file_path

        elif "resources.md" in filename:
            resources_file = file_path

        else:
            # Check for numbered lab files (e.g., 01-lab.md)
            file_pattern = re.compile(r'^\d{2}-.+\.md$')
            if file_pattern.match(filename):
                numbered_files.append(file_path)

    files_to_process = []

    if not introduction_file:
        intro_check = input("No '00-introduction.md' found. Do you want to proceed? (y/n) ")
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

    # Add introduction file first
    if introduction_file:
        files_to_process.append(introduction_file)

    # Sort numbered files and add them to the list
    numbered_files.sort()
    files_to_process.extend(numbered_files)

    # Append resources file, renaming it to the next number in the sequence
    if resources_file:
        last_number = int(numbered_files[-1].split('-')[0]) if numbered_files else 0
        new_resources_file_name = f"{last_number + 1:02d}-resources.md"
        new_resources_file_path = os.path.join(source_path, new_resources_file_name)
        os.rename(resources_file, new_resources_file_path)
        files_to_process.append(new_resources_file_path)

    if not files_to_process:
        print("No files matched the expected naming conventions.")
        return None

    # Merge the files
    for file_path in files_to_process:
        with open(file_path, 'r', encoding="utf-8") as file:
            merged_source_files += file.read() + '\n'
            print(f"Reading {file_path}")

    return merged_source_files