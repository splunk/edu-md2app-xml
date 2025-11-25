import os
import sys
import yaml
import ntpath
import importlib.resources
import logging
import shutil # <--- ADD THIS IMPORT
import pathlib

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


def copy_static_assets(source_base_dir, static_path):
    """
    Copies all assets from a 'static' folder in the source directory to the static_path folder.
    
    Args:
        source_base_dir (str): The root directory where the source 'static' folder is located.
                                E.g., '/path/to/your/project'
        static_path (pathlib.Path or str): The absolute path to the static directory where assets
                                           should be copied.
                                           E.g., '/path/to/your/output_app/appserver/static'
    """
    source_static_folder = os.path.join(source_base_dir, 'static')
    
    if not os.path.isdir(source_static_folder):
        logging.info(f"No 'static' folder found in source directory: {source_base_dir}. Skipping static asset copy.")
        return
    
    # Convert to string if it's a Path object
    target_static_folder = str(static_path)
    
    logging.info(f"Found 'static' folder in source directory. Copying assets from '{source_static_folder}' to '{target_static_folder}'")
    
    # Ensure the target directory exists
    os.makedirs(target_static_folder, exist_ok=True)
    
    try:
        # Walk through all files and subdirectories in the source static folder
        for root, dirs, files in os.walk(source_static_folder):
            # Calculate the relative path from the source static folder
            relative_path = os.path.relpath(root, source_static_folder)
            
            # Create the corresponding directory in the target
            if relative_path == '.':
                # We're in the root of the static folder
                destination_dir = target_static_folder
            else:
                destination_dir = os.path.join(target_static_folder, relative_path)
            
            # Ensure destination directory exists
            os.makedirs(destination_dir, exist_ok=True)
            logging.debug(f"Ensured directory exists: {destination_dir}")
            
            # Copy all files in this directory
            for file in files:
                source_file_path = os.path.join(root, file)
                destination_file_path = os.path.join(destination_dir, file)
                
                try:
                    shutil.copy2(source_file_path, destination_file_path)
                    logging.info(f"Copied static asset: {file} to {destination_file_path}")
                except Exception as e:
                    logging.error(f"Failed to copy static asset {source_file_path} to {destination_file_path}: {e}")
    
    except Exception as e:
        logging.error(f"Error walking through static folder {source_static_folder}: {e}")
    
    logging.info("Static asset copying process completed.")


def process_download_links(html_content, md_files_path, static_path, app_dir, course_title=None):
    """
    Processes download links in HTML content to copy linked assets and update the HTML with new URLs.
    
    Args:
        html_content (str): HTML content to process
        md_files_path (str): Path where markdown files are located
        static_path (pathlib.Path or str): Path to the static directory in the app
        app_dir (str): Name of the app directory for URL generation
        course_title (str): Course title for template variable replacement (legacy support)
        
    Returns:
        str: Updated HTML content with processed download links
    """
    import re
    import glob
    from urllib.parse import unquote
    
    if not html_content:
        return html_content
    
    logging.info(f"Processing download links...")
    
    # Create downloads directory in static folder
    downloads_dir = pathlib.Path(static_path) / 'downloads'
    downloads_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Created downloads directory: {downloads_dir}")
    
    # Regex to find HTML links: <a href="path">text</a>
    link_pattern = r'<a\s+[^>]*href=["\'](([^"\']+))["\']\s*[^>]*>([^<]+)</a>'
    
    # Find all links first for debugging
    all_links = re.findall(link_pattern, html_content)
    logging.info(f"Found {len(all_links)} links to process: {[link[0] for link in all_links]}")
    
    def replace_link(match):
        full_tag = match.group(0)
        original_path = match.group(1)
        link_text = match.group(3)
        
        logging.info(f"Processing link: {original_path}")
        
        # Skip if it's already a URL (http, https, etc.)
        if original_path.startswith(('http://', 'https://', 'mailto:', '#', '/static/')):
            logging.info(f"Skipping external/processed link: {original_path}")
            return full_tag  # Return unchanged
        
        # Handle legacy template variables like {course_title}
        processed_path = original_path
        if course_title and '{course_title}' in processed_path:
            processed_path = processed_path.replace('{course_title}', course_title)
            logging.info(f"Replaced template variable: {original_path} -> {processed_path}")
        
        md_files_path_obj = pathlib.Path(md_files_path)
        
        # Check if this is a wildcard pattern (contains *)
        if '*' in processed_path:
            logging.info(f"Processing wildcard pattern: {processed_path}")
            
            # For wildcard patterns, resolve relative to the md_files_path directory
            # where the downloads.md file is located
            if processed_path.startswith('./'):
                # ./ means same directory as the downloads.md file
                search_pattern = processed_path[2:]  # Remove ./
                search_path = md_files_path_obj / search_pattern
            elif processed_path.startswith('../'):
                # ../ means parent directory relative to downloads.md file location
                search_path = md_files_path_obj.parent / processed_path[3:]  # Remove ../
            else:
                # Absolute or relative path from md_files_path
                search_path = md_files_path_obj / processed_path
            
            logging.info(f"Searching for files with pattern: {search_path}")
            
            # Use glob to find matching files
            matching_files = glob.glob(str(search_path))
            logging.info(f"glob.glob('{search_path}') returned: {matching_files}")
            
            if not matching_files:
                logging.warning(f"No files found matching pattern: {search_path}")
                return full_tag  # Return unchanged if no matches
            
            if len(matching_files) > 1:
                logging.warning(f"Multiple files match pattern {search_path}: {matching_files}. Using first match.")
            
            # Use the first matching file
            source_file_path = pathlib.Path(matching_files[0])
            logging.info(f"Using matched file: {source_file_path}")
            
        else:
            # Handle regular file path (non-wildcard)
            source_file_path = (md_files_path_obj / processed_path).resolve()
            logging.info(f"Looking for file at: {source_file_path}")
            
            if not source_file_path.exists():
                logging.warning(f"Download asset not found: {source_file_path} (referenced as {original_path})")
                return full_tag  # Return unchanged if file doesn't exist
        
        # Get the filename
        filename = source_file_path.name
        
        # Check if file already exists in downloads directory to avoid duplicate copying
        destination_path = downloads_dir / filename
        
        if not destination_path.exists():
            try:
                # Copy the file to the downloads directory
                shutil.copy2(source_file_path, destination_path)
                logging.info(f"Copied download asset: {source_file_path.name} -> downloads/{filename}")
            except Exception as e:
                logging.error(f"Failed to copy download asset {source_file_path}: {e}")
                return full_tag  # Return unchanged if copy fails
        else:
            logging.debug(f"Download asset already exists: downloads/{filename}")
        
        # Generate the new URL for the Splunk app
        new_url = f"/static/app/{app_dir}/downloads/{filename}"
        
        # Replace the href in the original tag
        updated_tag = re.sub(r'href=["\'][^"\']*["\']', f'href="{new_url}"', full_tag)
        
        logging.info(f"Updated link: {original_path} -> {new_url}")
        return updated_tag
    
    # Replace all HTML links in the content
    updated_html = re.sub(link_pattern, replace_link, html_content)
    
    return updated_html