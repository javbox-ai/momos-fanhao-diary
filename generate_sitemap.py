import os
import glob
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom

# --- Configuration ---
BASE_URL = "https://momo-fanhao-diary.example.com"  # !! 請替換為您的實際網站 URL !!
STATIC_SITE_DIR = 'static_site'
OUTPUT_FILE = os.path.join(STATIC_SITE_DIR, 'sitemap.xml')

# --- Helper Function ---
def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

# --- Main Logic ---
def generate_sitemap():
    """Generates the sitemap.xml file.
    """
    print(f"Starting sitemap generation for directory: {STATIC_SITE_DIR}")
    
    # Create the root element <urlset>
    urlset = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # Find all HTML files recursively within the static site directory
    html_files = glob.glob(os.path.join(STATIC_SITE_DIR, '**/*.html'), recursive=True)
    print(f"Found {len(html_files)} HTML files.")

    for html_file in html_files:
        # Get the relative path from the static site directory
        relative_path = os.path.relpath(html_file, STATIC_SITE_DIR).replace('\\', '/')
        
        # Construct the absolute URL
        loc = f"{BASE_URL}/{relative_path}"
        
        # Get the last modification time
        try:
            lastmod_timestamp = os.path.getmtime(html_file)
            lastmod = datetime.fromtimestamp(lastmod_timestamp).strftime('%Y-%m-%d')
        except OSError:
            lastmod = datetime.now().strftime('%Y-%m-%d') # Fallback to current date
            print(f"Warning: Could not get modification time for {html_file}. Using current date.")

        # Determine change frequency and priority (simple example)
        if 'index' in relative_path:
            changefreq = 'daily'
            priority = '1.0'
        elif 'categories/' in relative_path or 'actresses/' in relative_path:
            changefreq = 'weekly'
            priority = '0.7'
        elif 'videos/' in relative_path:
            changefreq = 'weekly'
            priority = '0.8'
        else:
            changefreq = 'monthly'
            priority = '0.5'

        # Create <url> element
        url_element = SubElement(urlset, 'url')
        SubElement(url_element, 'loc').text = loc
        SubElement(url_element, 'lastmod').text = lastmod
        SubElement(url_element, 'changefreq').text = changefreq
        SubElement(url_element, 'priority').text = priority

    # Generate the XML string
    xml_string = prettify_xml(urlset)

    # Write the sitemap to the output file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        print(f"Sitemap successfully generated: {OUTPUT_FILE}")
    except IOError as e:
        print(f"Error writing sitemap file: {e}")

# --- Execution --- 
if __name__ == "__main__":
    generate_sitemap()