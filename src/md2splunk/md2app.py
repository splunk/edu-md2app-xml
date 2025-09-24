import argparse
import shutil
import os
import re
import yaml
import sys
import pathlib
import ntpath
import logging

from md2splunk.xml_generator import generate_nav, generate_guides
# Updated import to get the new image copying function
from md2splunk.file_handler import read_file, write_file, load_metadata, copy_images_with_subfolders

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# --- Top-level functions (generate_app_dot_conf, generate_metadata, etc.) ---
# These functions are defined directly in md2app.py, so they don't need to be imported from file_handler.

def generate_app_dot_conf(default_path, course_title, version, description):
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
        '''
    app_dot_conf_path = pathlib.Path(default_path, 'app.conf')
    write_file(app_dot_conf_path, app_dot_conf)


def generate_metadata(metadata_path):
    file = '''[]
access = read : [ * ], write : [ supportUser ]
export = system

[savedsearches]
owner = supportUser
        '''
    default_meta_path = pathlib.Path(metadata_path, 'default.meta')
    write_file(default_meta_path, file)


# --- REMOVE THE OLD copy_images_to_static FUNCTION FROM HERE ---
# It is replaced by the one in file_handler.py
# def copy_images_to_static(source_path, static_path):
#     try:
#         images_src_dir = pathlib.Path(source_path, 'images')
#         images_dst_dir = pathlib.Path(static_path, 'images')
#         # ... (old limited implementation) ...
#     except Exception as e:
#         logging.error(f"Error copying images: {e}")
#         sys.exit(1)


import importlib.resources # Make sure this import is at the top of main.py

def copy_styles(static_path: str):
    """Copy the default dashboard.css to the static_path."""
    try:
        static_path = pathlib.Path(static_path)
        static_path.mkdir(parents=True, exist_ok=True)

        # Use importlib.resources to reliably get the path to dashboard.css within the package
        # This will point to your source file when installed in editable mode.
        with importlib.resources.path('md2splunk.static', 'dashboard.css') as dashboard_css_src_path:
            shutil.copy(dashboard_css_src_path, static_path / 'dashboard.css')
            logging.info(f"Copied dashboard.css from package resources to {static_path / 'dashboard.css'}")

    except Exception as e:
        logging.exception("Failed to copy dashboard.css.")
        sys.exit(1)


def copy_custom_css_to_static(source_path: str, static_path: str):
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
    try:
        format = 'zip'
        parent_dir = os.path.dirname(output_path)
        archive_name = pathlib.Path(parent_dir, app_dir)

        shutil.make_archive(archive_name, format, parent_dir, os.path.basename(output_path))
        logging.info(f"App packaged successfully as {archive_name}.{format}")

    except Exception as e:
        logging.error(f"Error packaging the app: {e}")
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

        logging.info(f"Initial source path provided: {args.source_path}")

        # Check if "lab-guides" subfolder exists and has contents
        lab_guides_path = pathlib.Path(args.source_path, "lab-guides")
        if lab_guides_path.is_dir() and any(lab_guides_path.iterdir()):
            logging.info(f"'lab-guides' folder found with content. Using it as the source path.")
            source_path = str(lab_guides_path)
        else:
            logging.info(f"'lab-guides' folder not found or empty. Using the provided source path.")
            source_path = args.source_path

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

    logging.info(f"Final source path in use: {source_path}")

    command = os.path.basename(sys.argv[0])
    guide_name_pattern = re.compile(r'^\d{2}-(?!.*answers).*\.md$')

    try:
        # Ensure the source path contains .md files
        md_files = [f for f in os.listdir(source_path) if f.endswith('.md')]
        if not md_files:
            logging.error(f"No .md files found in {source_path}")
            logging.error("Are you in the right directory?")
            sys.exit(1)

        if not any(re.search(guide_name_pattern, s) for s in md_files):
            logging.error("No guide files found.")
            sys.exit(1)

    except Exception as e:
        logging.error(f"Error processing source path {source_path}: {e}")
        sys.exit(1)

    # Load metadata from the source path
    metadata = load_metadata(source_path)

    # Read metadata and set up app variables
    course_title = metadata.get("course_title")
    version = metadata.get("version")
    app_dir = course_title.lower().replace(" ", "_") + "_app"
    description = metadata.get("description")

    # Set up directory paths for the app structure
    output_path = pathlib.Path(source_path, app_dir) # This is the app's root directory
    os.makedirs(output_path, exist_ok