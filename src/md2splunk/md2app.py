import argparse
import shutil
import os
import re
import yaml
import sys
import pathlib
import ntpath
import logging
import importlib.resources # <--- THIS IS THE FIX: Ensure importlib is imported here

# Import necessary functions from your other modules
from md2splunk.xml_generator import generate_nav, generate_guides
# Ensure copy_images_with_subfolders, copy_static_assets, copy_app_icons, and process_download_links are imported from file_handler
from md2splunk.file_handler import read_file, write_file, load_metadata, copy_images_with_subfolders, copy_static_assets, copy_app_icons, process_download_links

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# --- Functions defined directly in md2app.py ---

def generate_app_dot_conf(default_path, course_title, version, description):
    """Generates the app.conf file for the Splunk app."""
    app_dot_conf = f'''[install]
is_configured = false
state = enabled
build = 1

[launcher]
author = Splunk LLC
version = {version}
description = {description}

[package]
check_for_updates = 0

[ui]
is_visible = true
label = {course_title}

[access]
read = *
write = admin,ess_admin
owner = nobody
roles = admin,ess_admin,ess_user
        
        '''
    app_dot_conf_path = pathlib.Path(default_path, 'app.conf')
    write_file(app_dot_conf_path, app_dot_conf)
    logging.info(f"Generated app.conf at {app_dot_conf_path}")


def generate_metadata(metadata_path):
    """Generates the default.meta file for the Splunk app."""
    file_content = '''[]
access = read : [ * ], write : [ supportUser ]
export = system

[savedsearches]
owner = supportUser
        '''
    default_meta_path = pathlib.Path(metadata_path, 'default.meta')
    write_file(default_meta_path, file_content)
    logging.info(f"Generated default.meta at {default_meta_path}")


def copy_styles(static_path: str):
    """Copy the default dashboard.css to the static_path."""
    try:
        static_path = pathlib.Path(static_path)
        static_path.mkdir(parents=True, exist_ok=True)

        # Use importlib.resources to reliably get the path to dashboard.css within the package
        with importlib.resources.path('md2splunk.static', 'dashboard.css') as dashboard_css_src_path:
            shutil.copy(dashboard_css_src_path, static_path / 'dashboard.css')
            logging.info(f"Copied dashboard.css from package resources to {static_path / 'dashboard.css'}")

    except Exception as e:
        logging.exception("Failed to copy dashboard.css.")
        sys.exit(1)


def copy_custom_css_to_static(source_path: str, static_path: str):
    """Copies custom.css if present, overwriting dashboard.css."""
    try:
        source_path = pathlib.Path(source_path)
        static_path = pathlib.Path(static_path)

        custom_css = source_path / 'custom.css'
        if custom_css.exists():
            shutil.copy(custom_css, static_path / 'dashboard.css')
            logging.info(f"custom.css found and used to overwrite dashboard.css in {static_path}")
        else:
            logging.info(f"No custom.css found in {source_path}; default dashboard.css remains")

    except Exception as e:
        logging.exception("Error copying custom.css")
        sys.exit(1)


def package_app(output_path, app_dir):
    """Packages the generated Splunk app into a .tar file."""
    try:
        format = 'tar'
        output_path = pathlib.Path(output_path)
        
        # Create the archive in the parent directory of the app
        parent_dir = output_path.parent
        archive_name = parent_dir / app_dir
        
        # Ensure the app directory exists before trying to package it
        if not output_path.exists():
            logging.error(f"App directory does not exist: {output_path}")
            sys.exit(1)
        
        # List contents to verify what we're packaging
        app_contents = list(output_path.iterdir())
        if not app_contents:
            logging.warning(f"App directory is empty: {output_path}")
        else:
            logging.info(f"Packaging app with {len(app_contents)} items: {[item.name for item in app_contents]}")

        # Create the tar archive with proper Splunk app structure
        # We need to archive from the parent directory and include the app directory
        parent_dir = output_path.parent
        app_dir_name = output_path.name
        shutil.make_archive(str(archive_name), format, str(parent_dir), app_dir_name)
        
        # Verify the archive was created
        archive_file = pathlib.Path(f"{archive_name}.{format}")
        if archive_file.exists():
            archive_size = archive_file.stat().st_size
            logging.info(f"App packaged successfully as {archive_file} (size: {archive_size} bytes)")
        else:
            logging.error(f"Archive was not created: {archive_file}")
            sys.exit(1)

    except Exception as e:
        logging.error(f"Error packaging the app: {e}")
        logging.exception("Full traceback:")
        sys.exit(1)


def main():
    # --- FIX: Initialize source_path here to prevent NameError ---
    source_path = None

    try:
        parser = argparse.ArgumentParser(description="App Builder")
        parser.add_argument('source_path', type=str, help="Path to the source directory")
        args = parser.parse_args()

        # Check if the provided source path is valid
        if not os.path.isdir(args.source_path):
            logging.error(f"{args.source_path} is not a valid directory.")
            sys.exit(1)

        logging.info(f"Source directory provided: {args.source_path}")

        # Keep the original source path for metadata and asset loading
        source_path = args.source_path
        
        # Determine where the markdown files are located (lab-guides subfolder or root)
        lab_guides_path = pathlib.Path(args.source_path, "lab-guides")
        if lab_guides_path.is_dir() and any(f.endswith('.md') for f in os.listdir(lab_guides_path) if os.path.isfile(os.path.join(lab_guides_path, f))):
            logging.info(f"'lab-guides' folder found with .md files. Processing guides from: {lab_guides_path}")
            md_files_path = str(lab_guides_path)
        else:
            logging.info(f"'lab-guides' folder not found or contains no .md files. Processing guides from root: {source_path}")
            md_files_path = source_path

    except argparse.ArgumentError as e:
        logging.error(f"Argument parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while parsing arguments: {e}")
        sys.exit(1)

    # --- Added check after the try-except block for robustness ---
    if source_path is None:
        logging.error("Source path could not be determined after argument parsing. Exiting.")
        sys.exit(1)

    logging.info(f"Metadata will be loaded from: {source_path}")
    logging.info(f"Markdown files will be processed from: {md_files_path}")

    command = os.path.basename(sys.argv[0])
    guide_name_pattern = re.compile(r'^\d{2}-(?!.*answers).*\.md$')

    try:
        # Ensure the markdown files path contains .md files
        md_files = [f for f in os.listdir(md_files_path) if f.endswith('.md')]
        if not md_files:
            logging.error(f"No .md files found in {md_files_path}")
            logging.error("Are you in the right directory?")
            sys.exit(1)

        if not any(re.search(guide_name_pattern, s) for s in md_files):
            logging.error("No guide files found matching the pattern.")
            sys.exit(1)

    except Exception as e:
        logging.error(f"Error processing markdown files path {md_files_path}: {e}")
        sys.exit(1)

    # Load metadata from the source path
    metadata = load_metadata(source_path)

    # Read metadata and set up app variables
    course_title = metadata.get("course_title", "Untitled App")
    version = metadata.get("version", "1.0.0")
    app_dir = course_title.lower().replace(" ", "_").replace("-", "_") + "_app" # Ensure valid app_dir
    description = metadata.get("description", "A Splunk App generated from Markdown guides.")

    # Set up directory paths for the app structure
    # output_path is the root of the new Splunk app (e.g., 'my_course_app')
    # If we're processing from lab-guides, put the app inside lab-guides directory
    # Otherwise, place it next to the source directory
    if md_files_path != source_path:  # We're using lab-guides
        output_path = pathlib.Path(md_files_path, app_dir)  # Place app inside lab-guides
        logging.info(f"Placing app inside lab-guides directory: {output_path}")
    else:  # We're processing from root
        output_path = pathlib.Path(pathlib.Path(source_path).parent, app_dir)  # Place app next to source
        logging.info(f"Placing app next to source directory: {output_path}")
    
    # Clean up existing output directory to ensure fresh build
    if output_path.exists():
        logging.info(f"Removing existing output directory: {output_path}")
        shutil.rmtree(output_path)
    
    os.makedirs(output_path, exist_ok=True)
    logging.info(f"App output directory: {output_path}")

    appserver_path = pathlib.Path(output_path, 'appserver')
    os.makedirs(appserver_path, exist_ok=True)

    default_path = pathlib.Path(output_path, 'default')
    os.makedirs(default_path, exist_ok=True)

    static_path = pathlib.Path(appserver_path, 'static')
    os.makedirs(static_path, exist_ok=True)

    # This images_path is the correct, final physical destination for your images
    images_path = pathlib.Path(static_path, 'images')
    os.makedirs(images_path, exist_ok=True) # Ensure this base directory exists

    panels_path = pathlib.Path(output_path, 'default/data/ui/panels/')
    os.makedirs(panels_path, exist_ok=True)

    views_path = pathlib.Path(output_path, 'default/data/ui/views')
    os.makedirs(views_path, exist_ok=True)

    metadata_path = pathlib.Path(output_path, 'metadata')
    os.makedirs(metadata_path, exist_ok=True)

    app_dict = {
        'source_path': source_path,
        'md_files_path': md_files_path,  # Path where .md files are located (lab-guides or root)
        'output_path': output_path,
        'appserver_path': appserver_path,
        'default_path': default_path,
        'static_path': static_path,
        'images_path': images_path, # This is correct for internal reference
        'panels_path': panels_path,
        'views_path': views_path,
        'metadata_path': metadata_path,
        'command': command,
        'app_dir': app_dir,
        'course_title': course_title,
        'guide_name_pattern': guide_name_pattern,
        'img_tag_regex': r'src=["\'](images/[^"\']+|./images/[^"\']+)["\']',
    }

    # Generate app components and package the app
    logging.info("=== Starting app component generation ===")
    
    logging.info("Generating metadata...")
    generate_metadata(metadata_path)
    
    logging.info("Generating app.conf...")
    generate_app_dot_conf(default_path, course_title, version, description)

    # --- Call the new, robust image copying function ---
    logging.info("Copying images...")
    copy_images_with_subfolders(
        source_base_dir=md_files_path,  # Look for images where the markdown files are
        final_images_target_dir=images_path # Pass the already calculated correct target
    )
    # --- END IMAGE COPYING CALL ---

    # Copy static assets from static folder if it exists (in md_files_path)
    logging.info("Checking for and copying static assets...")
    copy_static_assets(
        source_base_dir=md_files_path,
        static_path=static_path
    )
    
    # Copy app icons to the app's static directory (output/static)
    logging.info("Checking for and copying app icons...")
    app_static_path = pathlib.Path(output_path, 'static')
    os.makedirs(app_static_path, exist_ok=True)
    copy_app_icons(
        source_base_dir=md_files_path,
        app_static_path=app_static_path
    )

    logging.info("Copying styles...")
    copy_styles(static_path)

    # Check for custom.css in the source_path and copy it
    custom_css_source = pathlib.Path(source_path) / 'custom.css'
    if custom_css_source.exists():
        logging.info("Copying custom CSS...")
        copy_custom_css_to_static(source_path, static_path)
    else:
        logging.info(f"No custom.css found in {source_path}. Using default styles.")

    logging.info("Generating navigation...")
    generate_nav(app_dict)
    
    logging.info("Generating guides...")
    generate_guides(app_dict) # This is where update_img_src will be called internally
    
    # Verify app contents before packaging
    logging.info(f"=== App generation complete. Verifying contents of {output_path} ===")
    if output_path.exists():
        for item in output_path.rglob('*'):
            if item.is_file():
                logging.info(f"Created: {item.relative_to(output_path)} (size: {item.stat().st_size} bytes)")
    else:
        logging.error(f"App directory was not created: {output_path}")
        sys.exit(1)
    
    logging.info("Packaging app...")
    package_app(output_path, app_dir)

    logging.info(f"App '{app_dir}' successfully built at {output_path}")


# --- The try-except block for the entire script execution must wrap the main() call ---
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(f"An unexpected error occurred during app generation: {e}", exc_info=True)
        sys.exit(1)