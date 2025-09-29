import os
import re
import markdown
from datetime import datetime
import logging # Ensure logging is imported here if not already

# Assuming update_img_src is in md2splunk.image_handler
from md2splunk.image_handler import update_img_src


def generate_html(pdf_dict, md):
    logging.debug(f"generate_html called with source_path: {pdf_dict.get('source_path')}")
    logging.debug(f"Markdown content length: {len(md)}")

    """
    Generate HTML from Markdown.

    Parameters:
    - md: Markdown.
    - pdf_dict: A dictionary containing various parameters like logo_path, course_title, etc.
                This dict should also contain 'img_tag_regex', 'command', 'app_dir'.

    Returns:
    - string: Pasteurized HTML
    """

    # See: https://facelessuser.github.io/pymdown-extensions/usage_notes/
    # See: https://facelessuser.github.io/pymdown-extensions/extensions/blocks/admonition/
    extensions = [
        'pymdownx.extra',
        'pymdownx.emoji',
        'pymdownx.blocks.admonition',
        'pymdownx.highlight',
        'pymdownx.blocks.details',
    ]

    logo_path = pdf_dict.get('logo_path')
    course_title = pdf_dict.get('course_title')
    # source_path = pdf_dict.get('source_path') # Not directly used in HTML generation here
    year = datetime.now().year
    opening_tags = f"""
<html>
    <head>
    </head>
    <body>
    <header id="header">
        <!-- set the height to match the header height -->
        <img src="{logo_path}" style=max-height:50px;width: auto;/>
        <hr>
    </header>
    <footer id="footer">
        <span>
            ©{datetime.now().year} Splunk LLC. All rights reserved.
        </span>
        <span style="content: counter(page)">
        </span>
    </footer>

"""

    closing_tags = """
    </body>
</html>
"""

    # See: https://python-markdown.github.io/extensions/fenced_code_blocks/
    # See: https://python-markdown.github.io/extensions/tables/
    html = markdown.markdown(md, extensions=extensions)
    html = f"{opening_tags}{html}{closing_tags}"

    # --- FIX: Uncomment this line and pass the correct dictionary ---
    # The pdf_dict (which is actually app_dict from main.py) contains all the necessary info
    html = update_img_src(pdf_dict, html) # Pass pdf_dict as the config dictionary
    # --- END FIX ---

    logging.debug("Generated HTML content after image src update:")
    # print(html) # Avoid printing large HTML to console unless debugging specific output
    return html