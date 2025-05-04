import os
import jinja2

# --- Configuration ---
TEMPLATE_DIR = 'templates'
OUTPUT_DIR = 'static_site'
TEMPLATE_FILE = '404.html'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, '404.html')
LANGUAGES = ['zh', 'en'] # Render for both languages, though the template handles switching

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- Jinja2 Setup ---
def create_jinja_env():
    """Creates and configures the Jinja2 environment."""
    template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    env = jinja2.Environment(loader=template_loader, autoescape=True)
    return env

# --- Main Logic ---
def render_static_404():
    """Renders the static 404 page."""
    env = create_jinja_env()
    template = env.get_template(TEMPLATE_FILE)

    # Render the template (can pass lang if needed, but template handles it)
    # For a generic 404, we might not need specific language context here
    # unless the links inside depend on it, which they do.
    # Let's render it once, assuming the template logic handles language display
    # or defaults appropriately. The links are relative now.
    try:
        # Render with a default language context if needed, or none if template handles it
        # The template uses 'lang if lang else 'zh'', so providing 'zh' is safe.
        rendered_html = template.render(lang='zh') # Default lang for context
        
        # Write the output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        print(f"Successfully rendered static 404 page: {OUTPUT_FILE}")

    except Exception as e:
        print(f"Error rendering static 404 page: {e}")

# --- Execution ---
if __name__ == "__main__":
    render_static_404()