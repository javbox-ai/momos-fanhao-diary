import os
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Assuming get_static_paths is in the same directory or accessible via PYTHONPATH
from get_static_paths import get_static_paths 

# --- Configuration ---
# Load environment variables from .env file in the project root
# Adjust the path to .env if your script is nested deeper
DOTENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env') # Goes up one level to project root
load_dotenv(DOTENV_PATH)

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASE_URL not found in .env file or environment variables.")

# Configure Jinja2 environment
# Assuming templates are in a 'templates' directory at the project root
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output') # Output rendered files here

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

# --- Rendering Logic ---
def render_page(template_name, output_filename, context):
    """Renders a single page."""
    template = env.get_template(template_name)
    
    # Add static paths to the context
    full_context = {
        **context, 
        **get_static_paths(BASE_URL) # Merge static paths into the context
    }
    
    html_content = template.render(full_context)
    
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Rendered {template_name} to {output_path}")

# --- Example Usage ---
def main():
    # Example: Render a page (e.g., an index page)
    # Replace with your actual data and logic
    page_data = {
        "title": "My Awesome Page",
        "header_text": "Welcome to the Site!",
        "items": ["Item 1", "Item 2", "Item 3"]
    }
    
    # This is the context you mentioned in your request
    # (excluding static paths, which are added by render_page)
    example_context = {
        "lang": "zh",
        "seo": {
            "title": "SEO Title for Example Page",
            "description": "This is an example page for SEO."
        },
        "data": page_data # Your specific page data
    }
    
    render_page(
        template_name="example_page_template.html", # Create this template file
        output_filename="example.html", 
        context=example_context
    )

    # Example: Render another page, perhaps using base.html directly or another specific template
    # For this example, let's assume you have a 'home.html' that might extend 'base.html'
    home_context = {
        "lang": "en",
        "seo": {"title": "Homepage"},
        "data": {"greeting": "Hello from the homepage!"}
    }
    # render_page(
    #     template_name="home.html", 
    #     output_filename="home.html", 
    #     context=home_context
    # )

if __name__ == "__main__":
    # Create a dummy .env file if it doesn't exist for this example to run
    if not os.path.exists(DOTENV_PATH):
        print(f"Warning: .env file not found at {DOTENV_PATH}. Creating a dummy one for example.")
        with open(DOTENV_PATH, 'w') as f:
            f.write("BASE_URL=http://localhost:8000/\n")
            print(f"Dummy .env created. Please configure your BASE_URL in {DOTENV_PATH}")

    # Create a dummy template for the example to run
    dummy_template_path = os.path.join(TEMPLATE_DIR, "example_page_template.html")
    if not os.path.exists(dummy_template_path):
        if not os.path.exists(TEMPLATE_DIR):
            os.makedirs(TEMPLATE_DIR)
        with open(dummy_template_path, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ seo.title if seo else data.title }}</title>
    <!-- Using dynamic static paths -->
    <link rel="stylesheet" href="{{ css_main_url }}">
    <link rel="icon" href="{{ logo_url }}"> <!-- Example: using logo_url as favicon -->
</head>
<body>
    <header>
        <img src="{{ logo_url }}" alt="Site Logo" width="100">
        <h1>{{ data.header_text if data and data.header_text else 'My Site' }}</h1>
    </header>
    
    <main>
        <p>This is an example page rendered with dynamic static paths.</p>
        <p>Base URL was: {{ get_static_paths(BASE_URL).css_main_url|replace('/static/css/main.css','') }}</p>
        <h2>Items:</h2>
        <ul>
            {% for item in data.items %}
            <li>{{ item }}</li>
            {% endfor %}
        </ul>
        <img src="{{ placeholder_image_url }}" alt="Placeholder">
        <img src="{{ cover_image_example_url }}" alt="Cover Example">
    </main>
    
    <footer>
        <p>&copy; 2024 My Site</p>
    </footer>
    
    <!-- Using dynamic static paths -->
    <script src="{{ js_main_url }}"></script>
</body>
</html>
            """)
        print(f"Dummy template created at {dummy_template_path}")
    main() 