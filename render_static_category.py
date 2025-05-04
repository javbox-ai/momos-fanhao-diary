import os
import jinja2
import random
from datetime import datetime
# Import necessary functions and the desired categories list from app.py
# Make sure app.py is in the Python path or adjust the import accordingly
from app import get_db_connection, DESIRED_CATEGORIES # Removed fetch_category_articles, will define a static version

# --- Configuration ---
TEMPLATE_DIR = 'templates'
# Define the output directory for static site category pages
OUTPUT_DIR = os.path.join('static_site', 'categories') 
TEMPLATE_FILE = 'category_static.html'
LANGUAGES = ['zh', 'en']

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- Jinja2 Setup ---
def create_jinja_env():
    """Creates and configures the Jinja2 environment."""
    template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    env = jinja2.Environment(loader=template_loader, autoescape=True)
    # Add any custom filters or global functions if needed
        # Add truncate filter if not built-in (Jinja2 usually has it)
    # env.filters['truncate'] = lambda s, length=255, killwords=False, end='...': ...
    return env

# --- Data Fetching (Adapt from app.py or create new) ---
def fetch_category_articles_static(category_name, limit=50):
    """Fetches articles for a specific category from the database."""
    conn = get_db_connection()
    if not conn:
        print(f"Error: Could not connect to database for category {category_name}")
        return []
    articles = []
    try:
        cursor = conn.cursor(dictionary=True)
        # Query to find videos associated with the genre name
        query = """
            SELECT
                v.code AS id,
                v.title,
                v.cover_url AS cover_image,
                v.description AS summary,
                GROUP_CONCAT(DISTINCT a.name) AS actress
            FROM videos v
            JOIN video_genre vg ON v.id = vg.video_id
            JOIN genres g ON vg.genre_id = g.id
            LEFT JOIN video_actress va ON v.id = va.video_id
            LEFT JOIN actresses a ON va.actress_id = a.id
            WHERE g.name = %s
            GROUP BY v.id
            ORDER BY v.release_date DESC
            LIMIT %s
        """
        cursor.execute(query, (category_name, limit))
        articles = cursor.fetchall()
        # Basic processing (similar to app.py)
        for article in articles:
            if not article.get('cover_image'):
                # Path relative to the final HTML location (static_site/categories/)
                article['cover_image'] = '../../static/placeholder.jpg'
            # Split actress string into list
            article['actress'] = article['actress'].split(',') if article.get('actress') else []
            article['summary'] = article.get('summary', '') # Ensure summary exists

        print(f"Fetched {len(articles)} articles for category '{category_name}'")
    except Exception as e:
        print(f"Error fetching articles for category {category_name}: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return articles

def get_top_favorites_for_static(limit=5):
    """Gets top favorite articles (simulated for static generation)."""
    # This is a placeholder. In reality, you'd fetch popular items.
    # For now, let's fetch some recent items as a substitute.
    conn = get_db_connection()
    if not conn:
        return []
    favorites = []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT v.code AS id, v.title
            FROM videos v
            ORDER BY v.release_date DESC -- Or some popularity metric
            LIMIT %s
        """
        cursor.execute(query, (limit * 5,)) # Fetch more to sample from
        all_recent = cursor.fetchall()
        if all_recent:
            actual_limit = min(limit, len(all_recent))
            sampled_favorites = random.sample(all_recent, actual_limit)
            # Format for template (matching expected structure)
            # The URL needs the language, but we fetch once. We'll add lang in the template or adjust here.
            # Adjust links for static site structure
            favorites = [
                {
                    'url_zh': f"../../videos/{fav['id']}_zh.html", 
                    'url_en': f"../../videos/{fav['id']}_en.html", 
                    'display_name': fav['title']
                } 
                for fav in sampled_favorites
            ]
            print(f"Generated {len(favorites)} simulated top favorites.")

    except Exception as e:
        print(f"Error fetching simulated top favorites: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return favorites

# --- Static Page Generation ---
def render_category_page(env, category_name, lang, all_genres, top_favorites):
    """Renders a single static category page."""
    print(f"Rendering category: {category_name} ({lang})...")
    template = env.get_template(TEMPLATE_FILE)

    # Fetch articles for this category
    articles_raw = fetch_category_articles_static(category_name, limit=50) # Use the static-safe function
    # Adjust article links for static site structure
    articles = []
    for article in articles_raw:
        article['link_zh'] = f"../../videos/{article['id']}_zh.html"
        article['link_en'] = f"../../videos/{article['id']}_en.html"
        articles.append(article)

    # Prepare context for the template
    context = {
        'category_name': category_name,
        'articles': articles,
        'all_genres': all_genres, # Pass the filtered list for sidebar links
        'top_5_favorites': top_favorites, # Pass top favorites
        'lang': lang,
        'breadcrumb_home_link': f"../../index_{lang}.html" # Add breadcrumb link
        # Add any other necessary context variables here
    }

    # Render the template
    try:
        html_content = template.render(context)
        # Define output filename (sanitize category name)
        safe_category_name = category_name.replace(' ', '_').replace('/', '_')
        output_filename = f"{safe_category_name}_{lang}.html"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Check if file already exists
        if os.path.exists(output_path):
            print(f"Skipping existing file: {output_path}")
        else:
            # Write the rendered HTML to a file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Successfully rendered: {output_path}")

    except Exception as e:
        print(f"Error rendering category {category_name} ({lang}): {e}")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting static category page generation...")
    start_time = datetime.now()
    jinja_env = create_jinja_env()

    # Fetch shared data once
    print("Fetching shared data (Top Favorites)...")
    # Simulate fetching top favorites (adjust lang handling if needed)
    # For static generation, we might use a single list or fetch per lang if logic differs
    top_5_static_favorites = get_top_favorites_for_static(limit=5)

    # Iterate through desired categories and languages
    print(f"Rendering for {len(DESIRED_CATEGORIES)} categories and {len(LANGUAGES)} languages...")

    # Iterate through desired categories and languages
    for category in DESIRED_CATEGORIES:
        for lang_code in LANGUAGES:
            # Pass the correct language-specific favorites if needed, or the general list
            render_category_page(jinja_env, category, lang_code, DESIRED_CATEGORIES, top_5_static_favorites)

    end_time = datetime.now()
    print("\nStatic category page generation finished.")
    print(f"Pages saved in: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Total time: {end_time - start_time}")
    print("Note: This script only generates the HTML files. You need to configure your web server to serve them from the 'static_site/categories' directory.")
    print("Run 'python render_static_category.py' to generate the pages when needed.")