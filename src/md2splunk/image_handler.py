import ntpath
import os
import re
import logging

logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() 
    ]
)

def update_img_src(dict, html_relative_src):
    """Updates the 'src' attribute in image tags within HTML content."""
    try:
        img_tag_regex = dict.get('img_tag_regex')
        source_path = dict.get('source_path')
        
        matches = re.findall(img_tag_regex, html_relative_src)
        html_absolute_src = html_relative_src

        if not matches: 
            logging.debug("No image tags found to update.")
            return html_absolute_src

        for src in matches:
            if src.startswith('images') or src.startswith('./images'):
                new_src = None

                if 'app' in dict.get('command', ''):
                    app_dir = dict.get('app_dir')
                    new_src = os.path.join("/static", "app", app_dir, "images", os.path.basename(src))
                    logging.debug(f"Updating image tags for app: {new_src}")
                else:
                    new_src = os.path.join(source_path, 'images', os.path.basename(src))
                    logging.debug(f"Updating image tags for static files: {new_src}")

                new_src = new_src.replace("\\", "/") 
                html_absolute_src = re.sub(r'src="' + re.escape(src) + '"', f'src="{new_src}"', html_absolute_src)

        logging.debug("Image tags updated.")
        return html_absolute_src

    except ValueError as e:
        logging.error(f"ValueError: {e}")
        return html_relative_src  
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return html_relative_src  
