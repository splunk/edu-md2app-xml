import os
import sys
import yaml
import ntpath
import importlib.resources
import logging
import shutil # <--- ADD THIS IMPORT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

def get_css_file_path(stylesheet):
    try:
        with importlib.resources.path('md2splunk.styles', stylesheet) as style_css_path:
            logging.info(f"Found CSS file: {style_css_path}")
            return style_css_path
    except Exception as e:
        logging.error(f"An error occurred while getting the CSS file path: {e}")
        raise RuntimeError(f"An error occurred while getting the CSS file path: {e}")


def get_custom_css_path(source_path):
    try:
        logging.info("Getting custom.css...")
        custom_css_path = os.path.join(source_path, "custom.css")
        logging.info(f"Custom CSS file path: {custom_css_path}")
        return os.path.normcase(f'{custom_css_path}')
    except Exception as e:
        logging.error(f"An error occurred while getting the custom CSS file path: {e}")
        raise RuntimeError(f"An error occurred while getting the custom CSS file path: {e}")

def get_logo_file_path():
    try:
        with importlib.resources.path('md2splunk.static', 'logo-splunk-cisco.png') as logo:
            logging.info(f"Found logo file: {logo}")
            return str(logo)
    except Exception as e:
        logging.error(f"An error occurred while getting the logo file path: {e}")
        raise RuntimeError(f"An error occurred while getting the logo file path: {e}")


def get_md_file(source_path, file):
    """
    Gets the content of a Markdown file.

    Parameters:
    - source_path: Path to directory containing Markdown files
    - file: Name of Markdown file

    Returns:
    - Content of the Markdown file

    Raises:
    - FileNotFoundError: If the file doesn't exist in the specified path.
    - IOError: If there is an issue with reading the file.
    """
    try:
        logging.info(f"Getting {file}...")
        file_path = os.path.join(source_path, file)

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Markdown file {file} not found at {file_path}")

        with open(file_path, 'r', encoding="utf-8") as md_file:
            content = md_file.read()
            logging.info(f"Successfully read the Markdown file: {file}")
            return content

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        raise FileNotFoundError(f"File not found: {e}")

    except IOError as e:
        logging.error(f"Error reading file {file}: {e}")
        raise IOError(f"Error reading file {file}: {e}")

    except Exception as e:
        logging.error(f"An unexpected error occurred while getting the Markdown file: {e}")
        raise RuntimeError(f"An unexpected error occurred while getting the Markdown file: {e}")


def read_file(file_path):
    """Helper function to read file content."""
    try:
        logging.debug(f"read_file called with file_path: {file_path}")
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                logging.info(f"Successfully read file: {file_path}")
                return content
        else:
            logging.error(f"File does not exist: {file_path}")
            raise FileNotFoundError(f"No {os.path.basename(file_path)} found at {file_path}.")
    except FileNotFoundError as e:
        logging.error(e)
        sys.exit(1)

def write_file(file_path, content):
    """Helper function to write content to a file."""
    try:
        # Ensure the directory exists before writing the file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
            logging.info(f"Successfully wrote content to file: {file_path}")
    except IOError as e:
        logging.error(f"Error writing to file {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while writing to the file: {e}")
        sys.exit(1)

def load_metadata(source_path):
    metadata_files = ['metadata.yml', 'metadata.yaml']
    for metadata_file in metadata_files:
        if os.name == 'nt':
            metadata_yaml = ntpath.join(source_path, metadata_file)
        else:
            metadata_yaml = os.path.join(source_path, metadata_file)

        if os.path.isfile(metadata_yaml):
            try:
                logging.info(f"Loading metadata from {metadata_yaml}...")
                with open(metadata_yaml, 'r', encoding="utf-8") as f:
                    metadata = yaml.safe_load(f)
                logging.info(f"Successfully loaded metadata.")
                return metadata
            except Exception as e:
                logging.error(f"Error loading or parsing {metadata_yaml}: {e}")
                sys.exit(1)

    # If we get here, no metadata file was found
    logging.error("No 'metadata.yaml' or 'metadata.yml' file found. It's a prerequisite 😉")
    sys.exit(1)


# NEW FUNCTION TO COPY IMAGE FILES WITH SUBFOLDERS (Corrected)
def copy_images_with_subfolders(source_base_dir, final_images_target_dir):
    """
    Copies image files from the source 'images' directory to the specified
    final target directory, preserving subfolder structure.

    Args:
        source_base_dir (str): The root directory where the source 'images' folder is located.
                                E.g., '/path/to/your/project'
        final_images_target_dir (pathlib.Path or str): The absolute path to the directory where images
                                       (including their subfolders) should be copied.
                                       E.g., '/path/to/your/output_app/appserver/static/images'
    """
    source_images_folder = os.path.join(source_base_dir, 'images')

    if not os.path.isdir(source_images_folder):
        logging.warning(f"Source images folder not found: {source_images_folder}. No images to copy.")
        return

    # The target_images_folder is now directly provided as final_images_target_dir
    target_images_folder = final_images_target_dir

    logging.info(f"Starting image copy from '{source_images_folder}' to '{target_images_folder}'")

    # Ensure the base target directory exists before walking
    os.makedirs(target_images_folder, exist_ok=True)

    for root, _, files in os.walk(source_images_folder):
        relative_path = os.path.relpath(root, source_images_folder)
        destination_dir = os.path.join(target_images_folder, relative_path)

        # Create destination directory if it doesn't exist
        os.makedirs(destination_dir, exist_ok=True)
        logging.debug(f"Ensured directory exists: {destination_dir}")

        for file in files:
            source_file_path = os.path.join(root, file)
            destination_file_path = os.path.join(destination_dir, file)

            try:
                # You might want to filter by image extensions here if not all files in 'images'
                # are actually images (e.g., .png, .jpg, .gif, .svg).
                # For now, it copies all files found.
                shutil.copy2(source_file_path, destination_file_path)
                logging.debug(f"Copied: {source_file_path} to {destination_file_path}")
            except Exception as e:
                logging.error(f"Failed to copy {source_file_path} to {destination_file_path}: {e}")

    logging.info("Image copying process completed.")