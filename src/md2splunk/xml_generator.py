import os
import re
import markdown
import datetime
from lxml import etree
from xml.dom import minidom

from md2splunk.html_generator import update_img_src
from md2splunk.file_handler import read_file, write_file

# https://facelessuser.github.io/pymdown-extensions/extensions/blocks/plugins/admonition/
extensions = [
    'fenced_code',
    'tables',
    'pymdownx.superfences',
    'pymdownx.emoji',
    'pymdownx.blocks.admonition',
    'pymdownx.blocks.details',
]

extension_configs = {
    "pymdownx.blocks.admonition": {
        'types': [
            'scenario',
            'note',
            'info',
            'tip',
            'hint',
            'caution',
            'warning',
            'danger',
            'custom'
        ]
    },
    "pymdownx.blocks.details": {
        'types': [
            'answers'
        ]
    }
}

opening_tags = '''<panel>
    <html>
        <style>

        </style>
        <body>
    '''

closing_tags = f'''<div>
                <p>©{datetime.datetime.now().year} Splunk LLC</p>
            </div>
        </body>
    </html>
</panel>
    '''


def convert_colons_to_blocks(md_text):
    # Normalize line endings
    md_text = md_text.replace('\r\n', '\n').replace('\r', '\n')

    # Convert ::: answers ... ::: to /// answers format for pymdownx.blocks.details
    def answers_replacer(match):
        content = match.group(1)
        
        # Check if answers block is indented (part of a list) by looking at the text before the match
        start_pos = match.start()
        text_before = md_text[:start_pos]
        
        # Look at the last three lines before this match
        lines_before = text_before.split('\n')[-3:] 
        
        # If we see numbered list items recently, treat as indented
        is_in_list = any(re.match(r'^\s*\d+\.', line) for line in lines_before)
        
        if is_in_list:
            # Use exactly 4 spaces for proper list item nesting
            indent = '    '
            # Re-indent all content lines to be consistent with the block indentation  
            content_lines = content.split('\n')
            indented_content = []
            for line in content_lines:
                if line.strip():  # If line has content
                    indented_content.append(indent + line.strip())
                else:  # Empty line
                    indented_content.append('')
            content = '\n'.join(indented_content)
        else:
            # No indentation for standalone blocks - just clean up the content
            indent = ''
            content = content.strip()
            
        # For list items, we need blank lines before and after the block for proper parsing
        if is_in_list:
            return f'\n{indent}/// answers\n{content}\n{indent}///\n'
        else:
            return f'{indent}/// answers\n{content}\n{indent}///'
    
    # Capture the block boundaries including any leading whitespace
    md_text = re.sub(
        r'^\s*:::\s*answers\s*\n(.*?)\n\s*:::\s*(?=\n|$)',
        answers_replacer,
        md_text,
        flags=re.DOTALL | re.MULTILINE
    )

    # Convert ::: <type> (excluding 'answers') to /// <type>
    md_text = re.sub(
        r'^:::\s*(?!answers\b)(\w+)\s*$',
        lambda m: f'/// {m.group(1)}',
        md_text,
        flags=re.MULTILINE
    )

    # Convert closing ::: to /// followed by a newline
    md_text = re.sub(
        r'^:::\s*(?:\n|\Z)',
        r'///\n',
        md_text,
        flags=re.MULTILINE
    )

    return md_text


def add_custom_styles(html):
    print("Applying custom CSS from file provided")
    h3_tag_regex = re.compile(r'(<h3[^>]*>)(.*?)(</h3>)', re.IGNORECASE | re.DOTALL)
    matches = re.findall(h3_tag_regex, html)

    for match in matches:
        opening_tag = match[0]
        content = match[1]
        closing_tag = match[2]

        if "Task" in content:
            if 'style' not in opening_tag:
                updated_opening_tag = f'{opening_tag.rstrip(">")}'
                updated_opening_tag += ' style="border-bottom: 1px solid black; padding: 5px; ">'
            else:
                updated_opening_tag = opening_tag.rstrip(">") + ' border-bottom: 1px solid black; padding: 5px;"' + ">"

            updated_tag = f'{updated_opening_tag}{content}{closing_tag}'
            html = html.replace(match[0] + match[1] + match[2], updated_tag)

    return html


def generate_nav(app_dict):
    source_path = app_dict.get('source_path')
    md_files_path = app_dict.get('md_files_path', source_path)  # Fallback to source_path for backward compatibility
    default_path = app_dict.get('default_path')
    guide_name_pattern = app_dict.get('guide_name_pattern')

    # Set the path to write the navigation XML
    nav_path = os.path.join(default_path, 'data', 'ui', 'nav')
    os.makedirs(nav_path, exist_ok=True)

    # Create the root <nav> element
    nav = etree.Element('nav', color="#154e7a")

    # Add the home view, pointing to "00-introduction" and marked as default
    home_view = etree.SubElement(nav, 'view', name="00-introduction", default="true")

    # Create a single <collection> for "Lab Guides"
    guides_collection = etree.SubElement(nav, 'collection', label="Lab Guides")

    # Add views to the collection, excluding "00-introduction"
    sorted_path = sorted(os.listdir(md_files_path))
    for file_name in sorted_path:
        if guide_name_pattern.match(file_name):
            view_name = os.path.splitext(file_name)[0]
            if view_name != "00-introduction":  # Exclude "00-introduction" from the collection
                etree.SubElement(guides_collection, 'view', name=view_name)

    # --- NEW FEATURE: Check for downloads.md and add to navigation if it exists ---
    downloads_md_path = os.path.join(md_files_path, "downloads.md")
    if os.path.exists(downloads_md_path): # Check if downloads.md exists. [5, 7, 8, 9, 10]
        print(f"Found {downloads_md_path}, adding 'Downloads' collection to navigation.")
        downloads_collection = etree.SubElement(nav, 'collection', label="Downloads") # Create new collection. [11, 12, 13, 14, 15]
        etree.SubElement(downloads_collection, 'view', name="downloads") # Add view for downloads. [11, 12, 13, 14, 15]

    # Convert the XML structure to a string
    xml_str = etree.tostring(nav, pretty_print=True, encoding='utf-8').decode()

    # Write the XML to the default.xml file
    default_xml_path = os.path.join(nav_path, "default.xml")
    write_file(default_xml_path, xml_str)

    print(f"default.xml generated at {default_xml_path}")

def generate_guides(app_dict):
    source_path = app_dict.get('source_path')
    md_files_path = app_dict.get('md_files_path', source_path)  # Fallback to source_path for backward compatibility
    views_path = app_dict.get('views_path')
    panels_path = app_dict.get('panels_path')
    app_dir = app_dict.get('app_dir')
    guide_name_pattern = app_dict.get('guide_name_pattern')

    # Iterate through all guide files in the markdown files directory
    for file_name in os.listdir(md_files_path):
        # --- MODIFIED CONDITION: Include downloads.md in processing ---
        # Process files matching the guide pattern OR if it's "downloads.md"
        if guide_name_pattern.match(file_name) or file_name == "downloads.md":
            view_name = os.path.splitext(file_name)[0]
            panel_name = os.path.splitext(file_name)[0] + '.xml'
            guide_path = os.path.join(md_files_path, file_name)

            # Read the guide file and process its content
            with open(guide_path, 'r', encoding="utf-8") as file:
                lines = file.readlines()

            # Determine guide title. For downloads.md, if the file is empty, use a default title.
            # Otherwise, extract from the first line, assuming it follows the '# Title' format.
            if file_name == "downloads.md" and not lines:
                guide_title = "Downloads"
            elif lines:
                guide_title = lines[0].strip()[2:]  # Extract the title from the first line
            else:
                guide_title = view_name.replace('-', ' ').title() # Fallback title if file is empty and not downloads.md

            preprocessed = ''.join(lines)

            # Create an individual dashboard XML for the guide
            dashboard = etree.Element('dashboard', version="1.1", stylesheet='dashboard.css', hideEdit="true")
            label = etree.SubElement(dashboard, 'label')
            label.text = guide_title
            row1 = etree.SubElement(dashboard, 'row')
            panel = etree.SubElement(row1, 'panel', ref=view_name, app=app_dir)

            # Write the dashboard XML
            xml_str = etree.tostring(dashboard, encoding='utf-8').decode()
            view_xml_path = os.path.join(views_path, view_name + '.xml')
            write_file(view_xml_path, xml_str)

            # Convert the Markdown content to HTML for the panel
            preprocessed = convert_colons_to_blocks(preprocessed)
            html = markdown.markdown(preprocessed, extensions=extensions, extension_configs=extension_configs)

            # Apply custom styles and update image paths
            html = update_img_src(app_dict, html)
            html = add_custom_styles(html)

            # Wrap the processed HTML with opening and closing tags
            content = f"{opening_tags}{html}{closing_tags}" # Using f-string for content. [1, 2, 3, 4, 6]
            panel_xml_path = os.path.join(panels_path, panel_name)

            # Write the panel content
            write_file(panel_xml_path, content)