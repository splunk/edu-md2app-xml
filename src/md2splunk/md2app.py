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
from md2splunk.file_handler import read_file, write_file, load_metadata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)


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


def generate_static_assets(output_path):
    try:
        static_path = pathlib.Path(output_path, 'static')
        os.makedirs(static_path, exist_ok=True)

        package_path = pathlib.Path(__file__).parent
        src_path = pathlib.Path(package_path, 'static')

        shutil.copytree(src_path, static_path, dirs_exist_ok=True)
        logging.info(f"Static assets copied to {static_path}")

    except Exception as e:
        logging.error(f"Error copying static assets: {e}")
        sys.exit(1)


def copy_images_to_static(source_path, static_path):
    try:
        images_src_dir = pathlib.Path(source_path, 'images')
        images_dst_dir = pathlib.Path(static_path, 'images')

        if os.path.exists(images_src_dir):
            if not os.path.exists(images_dst_dir):
                os.makedirs(images_dst_dir)

            for image_file in os.listdir(images_src_dir):
                if image_file.endswith('.png'):
                    image_src_path = pathlib.Path(images_src_dir, image_file)
                    image_dst_path = pathlib.Path(images_dst_dir, image_file)
                    shutil.copy(image_src_path, image_dst_path)
            logging.info(f"Copied images from {images_src_dir} to {images_dst_dir}")
        else:
            logging.warning(f"No 'images' directory found in {images_src_dir}")

    except Exception as e:
        logging.error(f"Error copying images: {e}")
        sys.exit(1)


def copy_styles(static_path: str):
    """Copy the default dashboard.css to the static_path."""
    try:
        static_path = pathlib.Path(static_path)
        static_path.mkdir(parents=True, exist_ok=True)

        # NEW: Conditional logic for Windows using os.name
        if os.name == 'nt':  # Check if the OS is Windows
            logging.info("Windows detected. Adjusting paths for Windows user installation.")

            # Define a user-writable directory (e.g., %APPDATA%)
            app_data_dir = pathlib.Path(os.getenv('APPDATA', './')) / 'md2splunk'
            app_data_static_dir = app_data_dir / 'static'

            # Ensure the directory exists
            app_data_static_dir.mkdir(parents=True, exist_ok=True)

            # Copy the static file to the user-writable directory if it doesn't exist
            dashboard_css_src = pathlib.Path(__file__).parent / 'static' / 'dashboard.css'
            dashboard_css_dest = app_data_static_dir / 'dashboard.css'

            if not dashboard_css_dest.exists():
                shutil.copy(dashboard_css_src, dashboard_css_dest)
                logging.info(f"Copied dashboard.css to {dashboard_css_dest}")

            # Update the path to use the copied file
            dashboard_css = dashboard_css_dest
        else:
            # Default behavior for non-Windows OSes
            dashboard_css = pathlib.Path('./src/md2splunk/static/dashboard.css')

        if not dashboard_css.exists():
            logging.error(f"dashboard.css not found at {dashboard_css}")
            sys.exit(1)

        shutil.copy(dashboard_css, static_path / 'dashboard.css')
        logging.info(f"Copied dashboard.css to {static_path}")

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
        if lab_guides_path.is_dir() and any(lab_guides_path.iterdir()):  # Check if directory exists and is not empty
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
    output_path = pathlib.Path(source_path, app_dir)
    os.makedirs(output_path, exist_ok=True)

    appserver_path = pathlib.Path(output_path, 'appserver')
    default_path = pathlib.Path(output_path, 'default')
    os.makedirs(default_path, exist_ok=True)

    static_path = pathlib.Path(appserver_path, 'static')
    os.makedirs(static_path, exist_ok=True)

    images_path = pathlib.Path(static_path, 'images')
    os.makedirs(images_path, exist_ok=True)

    panels_path = pathlib.Path(output_path, 'default/data/ui/panels/')
    os.makedirs(panels_path, exist_ok=True)

    views_path = pathlib.Path(output_path, 'default/data/ui/views')
    os.makedirs(views_path, exist_ok=True)

    metadata_path = pathlib.Path(output_path, 'metadata')
    os.makedirs(metadata_path, exist_ok=True)

    app_dict = {
        'source_path': source_path,
        'output_path': output_path,
        'appserver_path': appserver_path,
        'default_path': default_path,
        'static_path': static_path,
        'images_path': images_path,
        'panels_path': panels_path,
        'views_path': views_path,
        'metadata_path': metadata_path,
        'command': command,
        'app_dir': app_dir,
        'guide_name_pattern': guide_name_pattern,
        'img_tag_regex': r'<img[^>]+src="([^"]+)"',
    }

    # Generate app components and package the app
    generate_metadata(metadata_path)
    generate_app_dot_conf(default_path, course_title, version, description)
    generate_static_assets(output_path)
    copy_images_to_static(source_path, static_path)
    copy_styles(static_path)

    for file in os.listdir(source_path):
        if file == 'custom.css':
            copy_custom_css_to_static(source_path, static_path)

    generate_nav(app_dict)
    generate_guides(app_dict)
    package_app(output_path, app_dir)

if __name__ == '__main__':
    main()