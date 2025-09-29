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
        if not img_tag_regex:
            logging.error("img_tag_regex not found in dictionary. Cannot process image tags.")
            return html_relative_src

        # source_path is used for 'else' branch, but not for 'app' command in this revised logic
        source_path = dict.get('source_path')

        matches = re.findall(img_tag_regex, html_relative_src)
        html_absolute_src = html_relative_src

        if not matches:
            logging.debug("No image tags found to update.")
            return html_absolute_src

        for src in matches:
            relative_path_after_images = None

            # This part extracts the path relative to the 'images' directory, preserving subfolders.
            # This is the critical logic for nested folders.
            if src.startswith('images/'):
                relative_path_after_images = src[len('images/'):]
            elif src.startswith('./images/'):
                relative_path_after_images = src[len('./images/'):]
            elif src == 'images' or src == './images': # Handle cases where src is just 'images'
                relative_path_after_images = ''
            else:
                # If src doesn't start with 'images/' or './images/', it's not handled by this logic
                # and we should skip it or log a warning.
                logging.debug(f"Image src '{src}' does not start with 'images/' or './images/'. Skipping.")
                continue # Skip to the next src in the loop

            if relative_path_after_images is not None:
                new_src = None

                # This block is for generating the correct Splunk web path
                # It *must* include "/static/app/<app_dir>/images/"
                if 'app' in dict.get('command', ''): # Assuming 'command' indicates app generation
                    app_dir = dict.get('app_dir')
                    new_src = os.path.join("/static", "app", app_dir, "images", relative_path_after_images)
                    logging.debug(f"Constructed new_src for app: {new_src} from original src: {src}")
                else:
                    # This 'else' branch would be for non-Splunk app contexts if your tool supports them.
                    # If not, you might simplify this logic.
                    new_src = os.path.join("/static", "images", relative_path_after_images) # Fallback or non-app static path
                    logging.debug(f"Constructed new_src for static files (non-app context): {new_src} from original src: {src}")

                new_src = new_src.replace("\\", "/") # Ensure forward slashes for web paths
                # Replace the original src with the new_src in the HTML
                # Use re.escape for src to handle special characters correctly in the regex pattern
                html_absolute_src = re.sub(r'src=["\']' + re.escape(src) + '["\']', f'src="{new_src}"', html_absolute_src)
            else:
                logging.debug(f"Skipping src not recognized as being within 'images' folder: {src}")

        logging.debug("Image tags updated.")
        return html_absolute_src

    except ValueError as e:
        logging.error(f"ValueError in update_img_src: {e}")
        return html_relative_src
    except Exception as e:
        logging.error(f"An unexpected error occurred in update_img_src: {e}", exc_info=True) # Add exc_info for traceback
        return html_relative_src
