import argparse
import shutil
import os
import re
import yaml
import sys
import pathlib
import ntpath
import logging

from md2splunk.xml_generator import generate_nav, generate_home, generate_guides
from md2splunk.file_handler import read_file, write_file, load_metadata

logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  
    ]
)

def generate_app_dot_conf(default_path, course_title, version, description):
    # Left-aligned for output formatting
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
    # Left-aligned for output formatting
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
        # Locally scoped static; not to be confused with /appserver/static
        static_path = pathlib.Path(output_path, 'static')
        os.makedirs(static_path, exist_ok=True)

        package_path = pathlib.Path(__file__).parent
        src_path = pathlib.Path(package_path, 'static')

        shutil.copytree(src_path, static_path, dirs_exist_ok=True)
        logging.info(f"Static assets copied to {static_path}")

    except Exception as e:
        logging.error(f"Error copying static assets: {e}")
        sys.exit(1)

        package_path = pathlib.Path(__file__).parent
        source_static_path = package_path / 'static'

        if not source_static_path.exists():
            logging.error(f"Source static directory does not exist: {source_static_path}")
            return

        try:
            shutil.copytree(source_static_path, output_static_path, dirs_exist_ok=True)
            logging.info(f"Copied static assets to: {output_static_path}")
        except shutil.Error as e:
            logging.error(f"Error copying static files: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error during static file copy: {e}")

    except Exception as e:
        logging.exception(f"Failed to generate static assets at {output_path}: {e}")


def copy_images_to_static(source_path, static_path):
    try:
        """Copy image files from the source directory, 'images', to the output destination directory, 'appserver/static/images'."""
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
    """If custom.css exists in the source_path, overwrite dashboard.css in static_path."""
    try:
        source_path = pathlib.Path(source_path)
        static_path = (pathlib.Path(static_path))

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
    """Package the app directory into a compressed file."""
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

        if not os.path.isdir(args.source_path):
            logging.error(f"{args.source_path} is not a valid directory.")
            sys.exit(1)

        logging.info(f"Using source path: {args.source_path}")

    except argparse.ArgumentError as e:
        logging.error(f"Argument parsing error: {e}")
        sys.exit(1)

    except Exception as e:
        logging.error(f"An unexpected error occurred while parsing arguments: {e}")
        sys.exit(1)
        

    source_path = args.source_path

    command = os.path.basename(sys.argv[0])
    guide_name_pattern = re.compile(r'^\d{2}-(?!.*answers).*\.md$')

    # CHECK FOR MARKDOWN FILES
    try:
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

    metadata = load_metadata(source_path)

    course_title = metadata.get("course_title")
    version = metadata.get("version")
    app_dir = course_title.lower().replace(" ", "_") + "_app"
    version = metadata.get("version")
    description = metadata.get("description")

    # NOTE this app uses the following naming conventions:
    #  `xyz_dir`: the directory name
    #  `xyz_path`: the full path of the directory or file    
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

    generate_metadata(metadata_path)

    generate_app_dot_conf(default_path, course_title, version, description)
    
    generate_static_assets(output_path)

    copy_images_to_static(source_path, static_path)

    copy_styles(static_path)

    for file in os.listdir(source_path):
        if file == 'custom.css':
            copy_custom_css_to_static(source_path, static_path)

    generate_nav(app_dict)

    generate_home(app_dict)

    generate_guides(app_dict)

    package_app(output_path, app_dir)


if __name__ == '__main__':
    main()