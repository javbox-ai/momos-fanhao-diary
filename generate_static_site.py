import os
import shutil
import pymysql
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from pathlib import Path
import math

print("--- Script execution started (v8 - removed featured_videos logic) ---") 

load_dotenv()
print("--- .env loaded (or attempted) (v8) ---")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
OUTPUT_DIR = "dist" 
TEMPLATES_DIR = "templates"
LANGUAGES = ["cn", "en"]
DEFAULT_LANG = "cn"
ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", 20))

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
TEST_LIMIT_TOTAL_VIDEOS = int(os.getenv("TEST_LIMIT_TOTAL_VIDEOS", 30)) 
TEST_LIMIT_VIDEOS_PER_CATEGORY = int(os.getenv("TEST_LIMIT_VIDEOS_PER_CATEGORY", 20))
TEST_LIMIT_PAGES_PER_CATEGORY = int(os.getenv("TEST_LIMIT_PAGES_PER_CATEGORY", 2))

def get_db_connection():
    return pymysql.connect(host=DB_HOST,
                           user=DB_USER,
                           password=DB_PASSWORD,
                           database=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor,
                           charset='utf8mb4')

def get_base_url(lang):
    return f"/{lang}" if lang != DEFAULT_LANG else ""

def get_alternate_lang_url(current_lang, path):
    alternate_lang = "en" if current_lang == "cn" else "cn"
    base_alternate = get_base_url(alternate_lang)
    if path and not path.startswith('/'):
        path = '/' + path
    if path == '/': 
        path = '/index.html' if alternate_lang != DEFAULT_LANG else '/index.html'
    
    if not base_alternate and path.startswith('/'):
        return path
    if base_alternate and path.startswith('/'):
         return f"{base_alternate}{path}"
    return f"{base_alternate}{path}"

def ensure_dir(directory_path):
    Path(directory_path).mkdir(parents=True, exist_ok=True)

def clear_output_dir():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    ensure_dir(OUTPUT_DIR)

def render_and_save(template, context, output_path, lang): 
    html_content = template.render(context)
    ensure_dir(os.path.dirname(output_path))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated: {output_path}")

def get_video_details(video_id, conn):
    with conn.cursor() as cursor:
        sql = """
        SELECT
            v.id, v.code, v.title, v.cover_url, v.description, 
            v.release_date, v.publisher, v.duration, v.created_at,
            GROUP_CONCAT(DISTINCT g.id ORDER BY g.name SEPARATOR ',') as genre_ids,
            GROUP_CONCAT(DISTINCT g.name ORDER BY g.name SEPARATOR ',') as genre_names,
            GROUP_CONCAT(DISTINCT a.id ORDER BY a.name SEPARATOR ',') as actress_ids,
            GROUP_CONCAT(DISTINCT a.name ORDER BY a.name SEPARATOR ',') as actress_names
        FROM videos v
        LEFT JOIN video_genre vg ON v.id = vg.video_id
        LEFT JOIN genres g ON vg.genre_id = g.id
        LEFT JOIN video_actress va ON v.id = va.video_id
        LEFT JOIN actresses a ON va.actress_id = a.id
        WHERE v.id = %s
        GROUP BY v.id;
        """
        cursor.execute(sql, (video_id,))
        video = cursor.fetchone()
        if video:
            if video['genre_ids'] and video['genre_names']:
                video['genres'] = [{'id': gid, 'name': name} for gid, name in zip(video['genre_ids'].split(','), video['genre_names'].split(','))]
            else:
                video['genres'] = []
            if video['actress_ids'] and video['actress_names']:
                video['actresses'] = [{'id': aid, 'name': name} for aid, name in zip(video['actress_ids'].split(','), video['actress_names'].split(','))]
            else:
                video['actresses'] = []
        return video

# MODIFIED: Removed featured_only parameter and related SQL logic
def get_all_videos(conn, lang, limit=None, offset=0, order_by="v.release_date DESC"):
    with conn.cursor() as cursor:
        sql = f"""
            SELECT
                v.id, v.code, v.title AS title, v.cover_url, v.release_date,
                GROUP_CONCAT(DISTINCT g.name ORDER BY g.name SEPARATOR ', ') as genres,
                GROUP_CONCAT(DISTINCT a.name ORDER BY a.name SEPARATOR ', ') as actresses
            FROM videos v
            LEFT JOIN video_genre vg ON v.id = vg.video_id
            LEFT JOIN genres g ON vg.genre_id = g.id
            LEFT JOIN video_actress va ON v.id = va.video_id
            LEFT JOIN actresses a ON va.actress_id = a.id
            GROUP BY v.id ORDER BY {order_by}
        """ # Removed WHERE clause for is_featured
        params = []
        if limit is not None: 
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

# MODIFIED: Removed featured_only parameter and related SQL logic
def get_total_videos_count(conn):
    with conn.cursor() as cursor:
        sql = "SELECT COUNT(DISTINCT v.id) as total FROM videos v"
        # Removed WHERE clause for is_featured
        cursor.execute(sql)
        return cursor.fetchone()['total']

def get_videos_by_genre(conn, genre_id, lang, limit=None, offset=0):
    with conn.cursor() as cursor:
        sql = f"""
            SELECT
                v.id, v.code, v.title AS title, v.cover_url, v.release_date,
                (SELECT GROUP_CONCAT(DISTINCT g_sub.name ORDER BY g_sub.name SEPARATOR ', ')
                 FROM genres g_sub JOIN video_genre vg_sub ON g_sub.id = vg_sub.genre_id
                 WHERE vg_sub.video_id = v.id) AS genres,
                (SELECT GROUP_CONCAT(DISTINCT a_sub.name ORDER BY a_sub.name SEPARATOR ', ')
                 FROM actresses a_sub JOIN video_actress va_sub ON a_sub.id = va_sub.actress_id
                 WHERE va_sub.video_id = v.id) AS actresses
            FROM videos v
            JOIN video_genre vg_main ON v.id = vg_main.video_id
            WHERE vg_main.genre_id = %s
            GROUP BY v.id ORDER BY v.release_date DESC
        """
        params = [genre_id]
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

def get_total_videos_by_genre_count(conn, genre_id):
    with conn.cursor() as cursor:
        sql = "SELECT COUNT(DISTINCT v.id) as total FROM videos v JOIN video_genre vg ON v.id = vg.video_id WHERE vg.genre_id = %s"
        cursor.execute(sql, (genre_id,))
        return cursor.fetchone()['total']

def get_videos_by_actress(conn, actress_id, lang, limit=None, offset=0):
    with conn.cursor() as cursor:
        sql = f"""
            SELECT
                v.id, v.code, v.title AS title, v.cover_url, v.release_date,
                (SELECT GROUP_CONCAT(DISTINCT g_sub.name ORDER BY g_sub.name SEPARATOR ', ')
                 FROM genres g_sub JOIN video_genre vg_sub ON g_sub.id = vg_sub.genre_id
                 WHERE vg_sub.video_id = v.id) AS genres,
                (SELECT GROUP_CONCAT(DISTINCT a_sub.name ORDER BY a_sub.name SEPARATOR ', ')
                 FROM actresses a_sub JOIN video_actress va_sub ON a_sub.id = va_sub.actress_id
                 WHERE va_sub.video_id = v.id) AS actresses
            FROM videos v
            JOIN video_actress va_main ON v.id = va_main.video_id
            WHERE va_main.actress_id = %s
            GROUP BY v.id ORDER BY v.release_date DESC
        """
        params = [actress_id]
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
        
def get_total_videos_by_actress_count(conn, actress_id):
    with conn.cursor() as cursor:
        sql = "SELECT COUNT(DISTINCT v.id) as total FROM videos v JOIN video_actress va ON v.id = va.video_id WHERE va.actress_id = %s"
        cursor.execute(sql, (actress_id,))
        return cursor.fetchone()['total']

def get_all_genres(conn, lang): 
    with conn.cursor() as cursor:
        sql = "SELECT id, name, (SELECT COUNT(*) FROM video_genre WHERE genre_id = genres.id) as video_count FROM genres ORDER BY video_count DESC, name ASC"
        cursor.execute(sql)
        return cursor.fetchall()

def get_genre_by_id(conn, genre_id, lang): 
    with conn.cursor() as cursor:
        sql = "SELECT id, name FROM genres WHERE id = %s"
        cursor.execute(sql, (genre_id,))
        return cursor.fetchone()

def get_all_actresses(conn): 
    with conn.cursor() as cursor:
        sql = "SELECT id, name, (SELECT COUNT(*) FROM video_actress WHERE actress_id = actresses.id) as video_count FROM actresses ORDER BY video_count DESC, name ASC"
        cursor.execute(sql)
        return cursor.fetchall()

def get_actress_by_id(conn, actress_id): 
    with conn.cursor() as cursor:
        sql = "SELECT id, name FROM actresses WHERE id = %s"
        cursor.execute(sql, (actress_id,))
        return cursor.fetchone()

def get_chips_data(conn, lang):
    genres = get_all_genres(conn, lang)[:10] 
    actresses = get_all_actresses(conn)[:10] 
    return {
        "genres": [{'id': g['id'], 'name': g['name'], 'type': "genre"} for g in genres],
        "actresses": [{'id': a['id'], 'name': a['name'], 'type': "actress"} for a in actresses]
    }
    
def generate_site(conn, env):
    print("Starting static site generation...")
    clear_output_dir()

    index_template = env.get_template("index_static.html")
    video_template = env.get_template("detail_static.html")
    genre_videos_list_template = env.get_template("category_static.html") 
    actress_videos_list_template = env.get_template("actress_static.html") 
    all_genres_overview_template = env.get_template("overview_static.html") 
    all_actresses_overview_template = env.get_template("overview_static.html")
    disclaimer_template = env.get_template("disclaimer_static.html")

    all_videos_for_sitemap = [] 

    for lang in LANGUAGES:
        base_url = get_base_url(lang)
        lang_output_dir = os.path.join(OUTPUT_DIR, lang) if lang != DEFAULT_LANG else OUTPUT_DIR
        ensure_dir(lang_output_dir)

        chips_data = get_chips_data(conn, lang)
        default_seo_info = {
            "cn": {"title": "番号日记", "description": "最新影片和评论"},
            "en": {"title": "Fanhao Diary", "description": "Latest videos and reviews"}
        }
        common_context_extras = {
            "lang": lang,
            "base_url": base_url, 
            "chips_data": chips_data,
            "seo": default_seo_info.get(lang, default_seo_info["en"]) 
        }

        print(f"Generating index pages for {lang}...")
        total_videos_overall_count = get_total_videos_count(conn)
        videos_to_paginate_count = TEST_LIMIT_TOTAL_VIDEOS if TEST_MODE and total_videos_overall_count > TEST_LIMIT_TOTAL_VIDEOS else total_videos_overall_count
        num_index_pages = math.ceil(videos_to_paginate_count / ITEMS_PER_PAGE)
        if TEST_MODE:
             num_index_pages = min(num_index_pages, TEST_LIMIT_PAGES_PER_CATEGORY) 
        if videos_to_paginate_count > 0 and num_index_pages == 0: num_index_pages = 1
        if videos_to_paginate_count == 0: num_index_pages = 1

        for i in range(num_index_pages):
            offset = i * ITEMS_PER_PAGE
            current_page_video_limit = ITEMS_PER_PAGE

            if TEST_MODE:
                if offset >= TEST_LIMIT_TOTAL_VIDEOS:
                    if i == 0 and videos_to_paginate_count == 0: pass 
                    else: break 
                if (offset + ITEMS_PER_PAGE) > TEST_LIMIT_TOTAL_VIDEOS:
                    current_page_video_limit = max(0, TEST_LIMIT_TOTAL_VIDEOS - offset)
                if current_page_video_limit == 0 and not (i == 0 and videos_to_paginate_count == 0) : break 
            
            # Renamed to latest_videos, as it's the primary listing now.
            latest_videos = get_all_videos(conn, lang, limit=current_page_video_limit, offset=offset, order_by="v.release_date DESC")
            if not latest_videos and i == 0 and videos_to_paginate_count == 0: latest_videos = [] 
            elif not latest_videos and i > 0 : break 

            page_path_segment = f"index_p{i+1}.html" if i > 0 else "index.html"
            page_path_for_alt_lang = f"/{page_path_segment}" 

            # MODIFIED: Removed featured_videos logic entirely

            index_seo_title = ("Home" if lang == "en" else "首页")
            if num_index_pages > 1 and i > 0: 
                index_seo_title = (f"Home - Page {i+1}" if lang == "en" else f"首页 - 第 {i+1} 页")
            
            context = {
                **common_context_extras, 
                "videos": latest_videos, # Changed from page_videos to latest_videos for clarity; also used to be featured_videos context
                # "featured_videos": [], # Removed featured_videos from context
                "current_page": i + 1, 
                "total_pages": num_index_pages, 
                "page_base": f"{base_url}/index_p" if num_index_pages > 1 else f"{base_url}/index.html", 
                "seo": {"title": index_seo_title, "description": "Latest video releases and reviews." if lang == "en" else "最新影片发布与评论。"},
                "alternate_lang_url": get_alternate_lang_url(lang, page_path_for_alt_lang)
            }
            render_and_save(index_template, context, os.path.join(lang_output_dir, page_path_segment), lang)
            if i == 0 and lang == DEFAULT_LANG:
                 render_and_save(index_template, context, os.path.join(OUTPUT_DIR, "index.html"), lang)

        print(f"Generating video detail pages for {lang}...")
        if TEST_MODE:
            videos_for_detail_page_generation_summary = get_all_videos(conn, lang, limit=TEST_LIMIT_TOTAL_VIDEOS, offset=0)
        else:
            videos_for_detail_page_generation_summary = get_all_videos(conn, lang, limit=None) 

        for video_summary in videos_for_detail_page_generation_summary:
            video_id = video_summary['id']
            video_obj = get_video_details(video_id, conn) 
            if video_obj:
                all_videos_for_sitemap.append({'id': video_id, 'lang': lang, 'code': video_obj['code']})
                
                related_videos = []
                if video_obj.get('genres') and video_obj['genres'][0].get('id') is not None:
                    first_genre_id = video_obj['genres'][0]['id']
                    temp_related = get_videos_by_genre(conn, first_genre_id, lang, limit=5) 
                    related_videos = [rel_vid for rel_vid in temp_related if rel_vid['id'] != video_id][:4]

                video_title_for_seo = video_obj.get('title', 'Video') 
                video_description_for_seo = (video_obj.get('description', '') or video_title_for_seo)[:150]

                page_path = f"videos/{video_obj['code']}.html" 
                context = {
                    **common_context_extras, 
                    "video": video_obj, 
                    "related_videos": related_videos, 
                    "seo": {"title": video_title_for_seo, "description": video_description_for_seo},
                    "alternate_lang_url": get_alternate_lang_url(lang, f"/{page_path}")
                }
                render_and_save(video_template, context, os.path.join(lang_output_dir, page_path), lang)

        print(f"Generating genre video list pages for {lang}...")
        all_available_genres = get_all_genres(conn, lang) 
        for genre_info in all_available_genres:
            genre_id = genre_info['id']
            genre_name = genre_info['name'] 
            
            total_videos_in_genre_actual = get_total_videos_by_genre_count(conn, genre_id)
            if TEST_MODE and total_videos_in_genre_actual == 0: continue 

            videos_to_paginate_for_genre = min(total_videos_in_genre_actual, TEST_LIMIT_VIDEOS_PER_CATEGORY) if TEST_MODE else total_videos_in_genre_actual
            num_genre_pages = math.ceil(videos_to_paginate_for_genre / ITEMS_PER_PAGE)
            if TEST_MODE: num_genre_pages = min(num_genre_pages, TEST_LIMIT_PAGES_PER_CATEGORY)
            if videos_to_paginate_for_genre > 0 and num_genre_pages == 0: num_genre_pages = 1
            if videos_to_paginate_for_genre == 0 : num_genre_pages = 1 

            for i in range(num_genre_pages):
                offset = i * ITEMS_PER_PAGE
                current_page_video_limit = ITEMS_PER_PAGE
                if TEST_MODE:
                    if offset >= TEST_LIMIT_VIDEOS_PER_CATEGORY: 
                        if i==0 and videos_to_paginate_for_genre == 0: pass
                        else: break
                    if (offset + ITEMS_PER_PAGE) > TEST_LIMIT_VIDEOS_PER_CATEGORY: current_page_video_limit = max(0, TEST_LIMIT_VIDEOS_PER_CATEGORY - offset)
                    if current_page_video_limit == 0 and not (i==0 and videos_to_paginate_for_genre ==0): break
                
                videos_in_genre = get_videos_by_genre(conn, genre_id, lang, limit=current_page_video_limit, offset=offset)
                if not videos_in_genre and i == 0 and videos_to_paginate_for_genre == 0 : videos_in_genre = []
                elif not videos_in_genre and i > 0: break

                page_num_suffix = f"_p{i+1}" if i > 0 else ""
                page_path = f"categories/{genre_id}{page_num_suffix}.html" 
                
                genre_page_seo_title = f"{genre_name}"
                if lang == "en": genre_page_seo_title += " Videos"
                else: genre_page_seo_title += " 影片"
                if i > 0: genre_page_seo_title += (f" - Page {i+1}" if lang == "en" else f" - 第 {i+1} 页")

                context = {
                    **common_context_extras, 
                    "category_type": "Genre" if lang == "en" else "分类", 
                    "category_name": genre_name, 
                    "category_id": genre_id, 
                    "videos": videos_in_genre, 
                    "current_page": i + 1, 
                    "total_pages": num_genre_pages, 
                    "page_base": f"{base_url}/categories/{genre_id}_p" if num_genre_pages > 1 else f"{base_url}/categories/{genre_id}.html",
                    "seo": {"title": genre_page_seo_title, "description": f"Watch {genre_name} videos." if lang == "en" else f"观看 {genre_name} 分类下的影片。"},
                    "alternate_lang_url": get_alternate_lang_url(lang, f"/{page_path}")
                }
                render_and_save(genre_videos_list_template, context, os.path.join(lang_output_dir, page_path), lang)

        print(f"Generating actress works list pages for {lang}...")
        all_available_actresses = get_all_actresses(conn) 
        for actress_info in all_available_actresses:
            actress_id = actress_info['id']
            actress_name = actress_info['name'] 
            
            total_videos_by_actress_actual = get_total_videos_by_actress_count(conn, actress_id)
            if TEST_MODE and total_videos_by_actress_actual == 0: continue

            videos_to_paginate_for_actress = min(total_videos_by_actress_actual, TEST_LIMIT_VIDEOS_PER_CATEGORY) if TEST_MODE else total_videos_by_actress_actual
            num_actress_pages = math.ceil(videos_to_paginate_for_actress / ITEMS_PER_PAGE)
            if TEST_MODE: num_actress_pages = min(num_actress_pages, TEST_LIMIT_PAGES_PER_CATEGORY)
            if videos_to_paginate_for_actress > 0 and num_actress_pages == 0: num_actress_pages = 1
            if videos_to_paginate_for_actress == 0: num_actress_pages = 1

            for i in range(num_actress_pages):
                offset = i * ITEMS_PER_PAGE
                current_page_video_limit = ITEMS_PER_PAGE
                if TEST_MODE:
                    if offset >= TEST_LIMIT_VIDEOS_PER_CATEGORY: 
                        if i==0 and videos_to_paginate_for_actress == 0: pass
                        else: break
                    if (offset + ITEMS_PER_PAGE) > TEST_LIMIT_VIDEOS_PER_CATEGORY: current_page_video_limit = max(0, TEST_LIMIT_VIDEOS_PER_CATEGORY - offset)
                    if current_page_video_limit == 0 and not (i==0 and videos_to_paginate_for_actress==0): break

                videos_by_actress = get_videos_by_actress(conn, actress_id, lang, limit=current_page_video_limit, offset=offset)
                if not videos_by_actress and i == 0 and videos_to_paginate_for_actress == 0: videos_by_actress = []
                elif not videos_by_actress and i > 0: break
                
                page_num_suffix = f"_p{i+1}" if i > 0 else ""
                page_path = f"actresses/{actress_id}{page_num_suffix}.html"

                actress_page_seo_title = f"{actress_name}"
                if lang == "en": actress_page_seo_title += " Works"
                else: actress_page_seo_title += " 作品" 
                if i > 0: actress_page_seo_title += (f" - Page {i+1}" if lang == "en" else f" - 第 {i+1} 页")
                
                context = {
                    **common_context_extras, 
                    "category_type": "Actress" if lang == "en" else "女优", 
                    "category_name": actress_name, 
                    "category_id": actress_id, 
                    "videos": videos_by_actress, 
                    "current_page": i + 1, 
                    "total_pages": num_actress_pages, 
                    "page_base": f"{base_url}/actresses/{actress_id}_p" if num_actress_pages > 1 else f"{base_url}/actresses/{actress_id}.html",
                    "seo": {"title": actress_page_seo_title, "description": f"All works by {actress_name}." if lang =="en" else f"女优 {actress_name} 的所有作品。"},
                    "alternate_lang_url": get_alternate_lang_url(lang, f"/{page_path}")
                }
                render_and_save(actress_videos_list_template, context, os.path.join(lang_output_dir, page_path), lang)

        print(f"Generating all genres overview page for {lang}...")
        all_g = get_all_genres(conn, lang) 
        overview_genres_title = "All Genres" if lang == "en" else "所有分類"
        context = {
            **common_context_extras, 
            "items": all_g, 
            "title": overview_genres_title, 
            "type": "genre", 
            "seo": {"title": overview_genres_title, "description": "Browse all video genres." if lang == "en" else "瀏覽所有影片分類。"},
            "alternate_lang_url": get_alternate_lang_url(lang, "/genres.html") 
        }
        render_and_save(all_genres_overview_template, context, os.path.join(lang_output_dir, "genres.html"), lang)

        print(f"Generating all actresses overview page for {lang}...")
        all_a = get_all_actresses(conn)
        overview_actresses_title = "All Actresses" if lang == "en" else "所有女优"
        context = {
            **common_context_extras, 
            "items": all_a, 
            "title": overview_actresses_title, 
            "type": "actress", 
            "seo": {"title": overview_actresses_title, "description": "Browse all actresses." if lang == "en" else "瀏覽所有女优。"},
            "alternate_lang_url": get_alternate_lang_url(lang, "/actresses.html") 
        }
        render_and_save(all_actresses_overview_template, context, os.path.join(lang_output_dir, "actresses.html"), lang)

        print(f"Generating disclaimer page for {lang}...")
        disclaimer_title = "Disclaimer" if lang == "en" else "免責聲明"
        context = {
            **common_context_extras, 
            "seo": {"title": disclaimer_title, "description": disclaimer_title}, 
            "alternate_lang_url": get_alternate_lang_url(lang, "/disclaimer.html")
        }
        render_and_save(disclaimer_template, context, os.path.join(lang_output_dir, "disclaimer.html"), lang)
        if lang == DEFAULT_LANG:
            render_and_save(disclaimer_template, context, os.path.join(OUTPUT_DIR, "disclaimer.html"), lang)

    print("Static site generation complete.")

if __name__ == "__main__":
    db_conn = None
    try:
        db_conn = get_db_connection()
        if db_conn:
            print("Successfully connected to the database.")
            
            if not os.path.isdir(TEMPLATES_DIR):
                print(f"Error: Templates directory '{TEMPLATES_DIR}' not found. Please ensure it exists in the same directory as the script (Expected: {os.path.abspath(TEMPLATES_DIR)}).")
                exit(1)

            essential_template_names = [
                "index_static.html", 
                "detail_static.html", 
                "category_static.html", 
                "actress_static.html",  
                "overview_static.html", 
                "disclaimer_static.html"
            ]
            missing_templates_found = False
            for tpl_name in essential_template_names:
                if not os.path.exists(os.path.join(TEMPLATES_DIR, tpl_name)):
                    print(f"Error: Essential template '{tpl_name}' not found in '{TEMPLATES_DIR}'. Please ensure it exists.")
                    missing_templates_found = True
            if missing_templates_found:
                print("Halting due to missing essential templates.")
                exit(1)
            
            print(f"All essential page templates found in: {os.path.abspath(TEMPLATES_DIR)}")
            print(f"Outputting to: {os.path.abspath(OUTPUT_DIR)}")
            if TEST_MODE:
                print("--- RUNNING IN TEST MODE ---")
                print(f"TEST_LIMIT_TOTAL_VIDEOS (for index listing & video details generation pool): {TEST_LIMIT_TOTAL_VIDEOS}")
                print(f"TEST_LIMIT_VIDEOS_PER_CATEGORY (max videos listed under each genre/actress): {TEST_LIMIT_VIDEOS_PER_CATEGORY}")
                print(f"TEST_LIMIT_PAGES_PER_CATEGORY (max pages for each genre/actress list): {TEST_LIMIT_PAGES_PER_CATEGORY}")
                print(f"ITEMS_PER_PAGE (videos per paginated page): {ITEMS_PER_PAGE}")
                print("-----------------------------")

            env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
            generate_site(db_conn, env)
        else:
            print("Failed to connect to the database. Please check your .env settings.")
            exit(1) 
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        import traceback
        print(traceback.format_exc())
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        if db_conn:
            db_conn.close()
            print("Database connection closed.")
