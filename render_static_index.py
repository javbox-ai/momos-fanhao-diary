import os
import jinja2
from datetime import datetime
import random
import glob # Added glob
# Import necessary functions and data from app.py or other modules
from app import get_db_connection, DESIRED_CATEGORIES

# --- Configuration ---
TEMPLATE_DIR = 'templates'
OUTPUT_DIR = 'static_site'  # Output directory for the static index pages
TEMPLATE_FILE = 'index.html'
LANGUAGES = ['zh', 'en']

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- Jinja2 Setup ---
def create_jinja_env():
    """Creates and configures the Jinja2 environment."""
    template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    env = jinja2.Environment(loader=template_loader, autoescape=True)
    # Add strftime filter if not default
    env.filters['strftime'] = lambda dt, fmt: dt.strftime(fmt)
    return env

# --- Data Fetching ---

# NEW function to get pages based on file modification time
def get_latest_generated_pages(videos_dir, limit=20): # Fetch more initially
    """Fetches latest generated static video pages based on modification time."""
    print(f"Scanning for latest generated pages in: {videos_dir}")
    pages = []
    try:
        # Find all language-specific HTML files in the videos directory
        search_pattern = os.path.join(videos_dir, '*_*.html')
        html_files = glob.glob(search_pattern)
        print(f"Found {len(html_files)} potential video pages.")

        for filepath in html_files:
            try:
                filename = os.path.basename(filepath)
                # Extract code and lang (e.g., ABC-123_zh.html)
                parts = filename.rsplit('.', 1)[0].rsplit('_', 1)
                if len(parts) == 2:
                    code, lang = parts
                    if lang in LANGUAGES: # Ensure it's a valid language suffix
                        mtime_ts = os.path.getmtime(filepath)
                        mtime_dt = datetime.fromtimestamp(mtime_ts)
                        # Use relative path from OUTPUT_DIR for the URL
                        relative_path = os.path.relpath(filepath, OUTPUT_DIR).replace('\\', '/')
                        pages.append({
                            'url': relative_path,
                            'display_name': code, # Use code as display name for now
                            'code': code, # Add code explicitly for DB lookup
                            'mtime': mtime_dt,
                            'lang': lang,
                            'filepath': filepath # Keep for debugging if needed
                        })
                    # else:
                    #     print(f"  Skipping file with invalid lang suffix: {filename}")
                # else:
                #     print(f"  Skipping file with unexpected format: {filename}")
            except Exception as e:
                print(f"  Error processing file {filepath}: {e}")

        # Sort pages by modification time, newest first
        pages.sort(key=lambda x: x['mtime'], reverse=True)

        print(f"Successfully processed {len(pages)} valid video pages.")
        # Return the top 'limit' pages
        return pages[:limit]

    except Exception as e:
        print(f"Error scanning for generated pages: {e}")
        return []


def get_top_favorites_for_static(limit=5):
    """Gets top favorite articles (simulated for static generation)."""
    conn = get_db_connection()
    if not conn:
        return []
    favorites = []
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetching based on release date as a proxy for popularity
        query = """
            SELECT v.code AS id, v.title
            FROM videos v
            ORDER BY v.release_date DESC
            LIMIT %s
        """
        # Fetch more to sample from, ensuring variety
        fetch_limit = max(limit * 3, 10)
        cursor.execute(query, (fetch_limit,))
        all_recent = cursor.fetchall()

        if all_recent:
            # Ensure we don't request more samples than available
            actual_limit = min(limit, len(all_recent))
            # Randomly sample from the fetched recent videos
            sampled_favorites = random.sample(all_recent, actual_limit)

            # Adjust links for static site structure (relative from root)
            favorites = [
                {
                    'url_zh': f"videos/{fav['id']}_zh.html",
                    'url_en': f"videos/{fav['id']}_en.html",
                    'display_name': fav['title'] # Use actual title for favorites
                }
                for fav in sampled_favorites
            ]
            print(f"Generated {len(favorites)} simulated top favorites for static index.")
        else:
            print("No recent videos found to generate favorites.")

    except Exception as e:
        print(f"Error fetching simulated top favorites: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return favorites

# --- Static Page Generation ---
def render_index_page(env, lang, latest_pages, all_genres, top_favorites):
    """Renders a single static index page."""
    print(f"Rendering index page ({lang})...")
    template = env.get_template(TEMPLATE_FILE)

    # Prepare context for the template
    context = {
        'latest_static_pages': latest_pages, # This list is now pre-filtered by language
        'all_genres': all_genres,
        'top_5_favorites': top_favorites, # This list is also pre-filtered by language
        'lang': lang,
        'current_year': datetime.now().year # Add current year
    }

    # Render the template
    try:
        html_content = template.render(context)
        output_filename = f"index_{lang}.html"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Write the rendered HTML to a file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Successfully rendered: {output_path}")

    except Exception as e:
        print(f"Error rendering index page ({lang}): {e}")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting static index page generation...")
    start_time = datetime.now()
    jinja_env = create_jinja_env()

    # Fetch shared data once
    print("Fetching shared data...")
    # Use the new function to get latest pages based on file mtime
    videos_path = os.path.join(OUTPUT_DIR, 'videos')
    # Fetch more initially to ensure enough per lang, then limit per language later
    latest_generated_pages_data = get_latest_generated_pages(videos_path, limit=20)

    top_5_static_favorites = get_top_favorites_for_static(limit=5)
    all_genres_list = DESIRED_CATEGORIES # Use the list from app.py

    # Fetch titles and genres for the latest pages from DB
    print("Fetching titles and genres for latest pages...")
    latest_codes = list(set(page['code'] for page in latest_generated_pages_data))
    video_details_map = {}
    if latest_codes:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                format_strings = ','.join(['%s'] * len(latest_codes))
                query = f"""
                    SELECT v.code, v.title, GROUP_CONCAT(DISTINCT g.name) AS genres
                    FROM videos v
                    LEFT JOIN video_genre vg ON v.id = vg.video_id
                    LEFT JOIN genres g ON vg.genre_id = g.id
                    WHERE v.code IN ({format_strings})
                    GROUP BY v.code, v.title
                """
                cursor.execute(query, tuple(latest_codes))
                results = cursor.fetchall()
                for row in results:
                    video_details_map[row['code']] = {
                        'title': row['title'],
                        'tags': row['genres'].split(',') if row['genres'] else []
                    }
                print(f"Fetched details for {len(video_details_map)} codes.")
            except Exception as e:
                print(f"Error fetching video details from DB: {e}")
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        else:
            print("Could not connect to DB to fetch video details.")

    # Iterate through languages
    print(f"Rendering for {len(LANGUAGES)} languages...")
    for lang_code in LANGUAGES:
        # Filter latest pages for the current language and add details
        lang_latest_pages = []
        for page in latest_generated_pages_data:
            if page['lang'] == lang_code:
                details = video_details_map.get(page['code'])
                if details:
                    page['title'] = details['title']
                    page['tags'] = details['tags']
                else: # Fallback if details not found
                    page['title'] = page['display_name'] # Use code as title
                    page['tags'] = []
                lang_latest_pages.append(page)
        lang_latest_pages = lang_latest_pages[:10] # Limit to 10 per language after adding details

        # Prepare language-specific favorite URLs
        lang_top_favorites = []
        for fav in top_5_static_favorites:
            lang_top_favorites.append({
                'url': fav[f'url_{lang_code}'],
                'display_name': fav['display_name']
            })

        render_index_page(jinja_env, lang_code, lang_latest_pages, all_genres_list, lang_top_favorites)

    end_time = datetime.now()
    print("\nStatic index page generation finished.")
    print(f"Pages saved in: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Total time: {end_time - start_time}")