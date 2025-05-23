import os
import re
import markdown
from datetime import datetime

from md2splunk.image_handler import update_img_src


def generate_html(pdf_dict, md):
    """
    Generate HTML from Markdown.

    Parameters: 
    - md: Markdown. 
    - logo_path: Path to the corporate logo for page header
    - course_title: Title of the course for footer
    - source_path: Path to the source file

    Returns: 
    - string: Pasteurized HTML
    """

    # See: https://facelessuser.github.io/pymdown-extensions/usage_notes/
    # See: https://facelessuser.github.io/pymdown-extensions/extensions/blocks/plugins/admonition/
    extensions = [
        'pymdownx.extra',
        'pymdownx.emoji',
        'pymdownx.blocks.admonition',
        'pymdownx.highlight',
        'pymdownx.blocks.details',
    ]

    # md = pdf_dict.get('md')
    logo_path = pdf_dict.get('logo_path')
    course_title = pdf_dict.get('course_title')
    source_path = pdf_dict.get('source_path')
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

    # html_absolute_src = update_img_src(img_tag_regex, html, source_path)
    print(html)
    return html


