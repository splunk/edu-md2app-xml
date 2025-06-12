import os
import sys
import yaml
import ntpath
import importlib.resources
import logging
import ntpath

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

