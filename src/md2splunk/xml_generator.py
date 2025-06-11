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
            'answers',
            'custom'
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
    print("entering convert colons function")
    import re

    # Normalize line endings
    md_text = md_text.replace('\r\n', '\n').replace('\r', '\n')

    # Convert ::: answers ... ::: to HTML <details> block with a trailing newline
    def answers_block_replacer(match):
        content = match.group(1).strip()
        return f'<details class="answers">\n<summary>Answers</summary>\n{content}\n</details>\n'

    md_text = re.sub(
        r'^:::\s*answers\s*\n(.*?)\n:::\s*(?:\n|\Z)',
        answers_block_replacer,
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
    print("entering custom css function")
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
    print("entering generate nav function")
    source_path = app_dict.get('source_path')
    default_path = app_dict.get('default_path')
    guide_name_pattern = app_dict.get('guide_name_pattern')

    nav_path = os.path.join(default_path, 'data', 'ui', 'nav')
    os.makedirs(nav_path, exist_ok=True)

    nav = etree.Element('nav', color="#154e7a")
    home_view = etree.SubElement(nav, 'view', name="home", default="true")
    guides_collection = etree.SubElement(nav, 'collection', label="Lab Guides")

    def create_collection(label, file_name_pattern):
        print("entering create collection function")
        sorted_path = sorted(os.listdir(source_path))
        collection = etree.SubElement(nav, 'collection', label=label)

        for file_name in sorted_path:
            if file_name_pattern.match(file_name):
                view_name = os.path.splitext(file_name)[0]
                etree.SubElement(collection, 'view', name=view_name)

        return collection


    create_collection("Lab Guides", guide_name_pattern)

    xml_str = etree.tostring(nav, pretty_print=True, encoding='utf-8').decode()
    default_xml_path = os.path.join(nav_path, "default.xml")

    write_file(default_xml_path, xml_str)


def generate_guides(app_dict):
    print("entering generate guides function")
    source_path = app_dict.get('source_path')
    views_path = app_dict.get('views_path')
    panels_path = app_dict.get('panels_path')
    app_dir = app_dict.get('app_dir')
    guide_name_pattern = app_dict.get('guide_name_pattern')

    for file_name in os.listdir(source_path):
        if guide_name_pattern.match(file_name):
            view_name = os.path.splitext(file_name)[0]
            panel_name = os.path.splitext(file_name)[0] + '.xml'
            guide_path = os.path.join(source_path, file_name)

            # Add dynamic view / collection naming
            with open(guide_path, 'r', encoding="utf-8") as file:
                lines = file.readlines()

            guide_title = lines[0].strip()[2:]
            # Toggle to strip title from each guide
            # lines = lines[1:]  
            preprocessed = ''.join(lines)

            dashboard = etree.Element('dashboard', version="1.1", stylesheet='custom.css', hideEdit="true")
            label = etree.SubElement(dashboard, 'label')
            label.text = guide_title
            row1 = etree.SubElement(dashboard, 'row')
            panel = etree.SubElement(row1, 'panel', ref=view_name, app=app_dir)
            xml_str = etree.tostring(dashboard, encoding='utf-8').decode()
            view_xml_path = os.path.join(views_path, view_name + '.xml')

            write_file(view_xml_path, xml_str)

            # file_path = os.path.join(source_path, file_name)
            preprocessed = convert_colons_to_blocks(preprocessed)
            html = markdown.markdown(preprocessed, extensions=extensions, extension_configs=extension_configs)

            html = update_img_src(app_dict, html)
            html = add_custom_styles(html)

            content = f"{opening_tags}{html}{closing_tags}"
            panel_xml_path = os.path.join(panels_path, panel_name)

            write_file(panel_xml_path, content)

def generate_home(app_dict):
    """Generate a panel for the app with resources or information specified on the homepage."""
    # Normalize the source path and retrieve paths from app_dict
    source_path = os.path.normpath(app_dict.get('source_path'))
    views_path = app_dict.get('views_path')
    panels_path = app_dict.get('panels_path')

    # Debugging: Log the source path and directory contents
    logging.info(f"Source path: {source_path}")
    logging.debug(f"Contents of source path: {os.listdir(source_path)}")

    # Step 1: Create the home.xml dashboard
    logging.info("Creating home.xml dashboard...")
    dashboard = etree.Element('dashboard', version="1.1", stylesheet='custom.css', hideEdit="true")

    # Add basic elements to the dashboard
    label = etree.SubElement(dashboard, 'label')
    label.text = 'Home'

    row1 = etree.SubElement(dashboard, 'row')
    pan1 = etree.SubElement(row1, 'panel', ref="introduction")
    row2 = etree.SubElement(dashboard, 'row')
    pan2 = etree.SubElement(row2, 'panel', ref="resources")

    # Generate XML string for the dashboard
    xml_str = etree.tostring(dashboard, pretty_print=True, encoding='utf-8').decode()
    home_xml_path = os.path.join(views_path, "home.xml")

    # Write the home.xml file
    write_file(home_xml_path, xml_str)
    logging.info(f"Successfully wrote home.xml to: {home_xml_path}")

    # Step 2: Look for the introduction file (00-introduction.md)
    intro_file = os.path.normpath(os.path.join(source_path, "00-introduction.md"))
    logging.debug(f"Looking for intro_file: {intro_file}")

    # Check if the introduction file exists
    if not os.path.isfile(intro_file):
        logging.error(f"No '00-introduction.md' found in the directory: {source_path}")
        sys.exit(1)

    # Step 3: Look for the resources file dynamically
    resource_file = None
    for filename in os.listdir(source_path):
        if filename.strip().lower().endswith("-resources.md"):
            resource_file = os.path.normpath(os.path.join(source_path, filename))
            logging.info(f"Resources file found: {resource_file}")
            break

    # Step 4: Process 00-introduction.md
    try:
        logging.debug(f"Intro file path before calling read_file: {intro_file}")
        preprocessed = read_file(intro_file)
        logging.debug(f"Successfully read introduction file: {intro_file}")

        preprocessed = convert_colons_to_blocks(preprocessed)
        intro_html = markdown.markdown(preprocessed, extensions=extensions, extension_configs=extension_configs)
        intro_html_w_updated_img_src = update_img_src(app_dict, intro_html)
        add_custom_styles(intro_html_w_updated_img_src)

        # Create the introduction.xml panel
        intro_panel = f"{opening_tags}{intro_html_w_updated_img_src}{closing_tags}"
        intro_xml_path = os.path.join(panels_path, 'introduction.xml')
        write_file(intro_xml_path, intro_panel)
        logging.info(f"Successfully wrote introduction panel to: {intro_xml_path}")

    except Exception as e:
        logging.error(f"Error processing introduction file: {e}")
        sys.exit(1)

    # Step 5: Process resources.md (if it exists)
    try:
        if resource_file and os.path.isfile(resource_file):
            logging.debug(f"Resource file path before calling read_file: {resource_file}")
            preprocessed = read_file(resource_file)
            logging.debug(f"Successfully read resources file: {resource_file}")

            preprocessed = convert_colons_to_blocks(preprocessed)
            resource_html = markdown.markdown(preprocessed, extensions=extensions, extension_configs=extension_configs)
            resource_html_w_updated_img_src = update_img_src(app_dict, resource_html)
            add_custom_styles(resource_html_w_updated_img_src)

            # Create the resources.xml panel
            resource_panel = f"{opening_tags}{resource_html_w_updated_img_src}{closing_tags}"
            resource_xml_path = os.path.join(panels_path, 'resources.xml')
            write_file(resource_xml_path, resource_panel)
            logging.info(f"Successfully wrote resources panel to: {resource_xml_path}")

    except Exception as e:
        logging.error(f"Error processing resources file: {e}")