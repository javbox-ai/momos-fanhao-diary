import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import jinja2
import logging
import re
import mysql.connector # Added for MySQL
from dotenv import load_dotenv # Added for .env

# --- 基本設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
PUBLIC_STATIC_DIR = PROJECT_ROOT / "public" / "static"

# Database Configuration from .env
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Jinja2 環境設定
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)
jinja_env.globals['current_year'] = datetime.now(timezone.utc).year

# Constants (can be adjusted)
NUM_LATEST_VIDEOS_INDEX = 10 # Number of videos on index page
NUM_POPULAR_GENRES_INDEX = 7 # Changed from categories to genres
NUM_POPULAR_ACTRESSES_INDEX = 7
# NUM_VIDEOS_PER_CATEGORY_PAGE = 8 # For later
# NUM_VIDEOS_PER_ACTRESS_PAGE = 8 # For later

# 測試用全域參數
TEST_LIMIT = 30  # 僅產生前 30 筆影片/分類/女優
VIDEOS_PER_PAGE = 20  # 每頁顯示 20 筆
FEATURED_COUNT = 6    # 精選推薦數量
HOT_RANK_COUNT = 6    # 熱門排行榜數量

def generate_filename_component(identifier):
    if identifier is None:
        return "unknown-id"
    name = str(identifier).lower()
    # Allow alphanumeric, hyphens. Replace others with hyphen.
    name = re.sub(r'[^a-z0-9_.-]', '-', name) 
    name = re.sub(r'-+', '-', name) # Collapse multiple hyphens
    name = name.strip('-')
    return name if name else "unknown-id" # Ensure not empty

# --- Database Helper Functions ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4' # Ensure UTF-8 for CJK characters
        )
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to database: {err}")
        # Check for common issues
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            logging.error("Access denied. Check username/password.")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            logging.error(f"Database '{DB_NAME}' does not exist.")
        else:
            logging.error(f"MySQL Error {err.errno}: {err.msg}")
        return None

def fetch_latest_videos_for_index(limit=NUM_LATEST_VIDEOS_INDEX):
    # limit 參數優先使用 TEST_LIMIT
    real_limit = min(limit, TEST_LIMIT) if TEST_LIMIT else limit
    conn = get_db_connection()
    if not conn:
        return []
    
    videos_data = []
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Main query for videos
        video_query = ("""
            SELECT 
                v.id AS video_id, v.code AS video_code, v.title AS video_title, 
                v.release_date, v.description AS video_description,
                v.cover_url, v.created_at
            FROM videos v
            ORDER BY v.release_date DESC, v.created_at DESC 
            LIMIT %s
        """)
        cursor.execute(video_query, (real_limit,))
        raw_videos = cursor.fetchall()
        cursor.close() # Close main cursor

        for row in raw_videos:
            video_file_code = generate_filename_component(row['video_code'] if row['video_code'] else str(row['video_id']))
            
            # Fetch first actress for this video
            actress_id_for_file = "unknown-actress"
            actress_name_for_template_cn = "未知女優"
            actress_name_for_template_en = "Unknown Actress" # Duplicate
            actress_id_val = None

            if row['video_id']:
                actress_cursor = conn.cursor(dictionary=True)
                video_actress_query = ("""
                    SELECT act.id AS actress_id, act.name AS actress_name
                    FROM actresses act
                    JOIN video_actress va ON act.id = va.actress_id
                    WHERE va.video_id = %s
                    LIMIT 1
                """)
                actress_cursor.execute(video_actress_query, (row['video_id'],))
                actress_row = actress_cursor.fetchone()
                actress_cursor.close()
                if actress_row:
                    actress_id_val = actress_row['actress_id']
                    actress_id_for_file = generate_filename_component(str(actress_row['actress_id']))
                    actress_name_for_template_cn = actress_row['actress_name']
                    actress_name_for_template_en = actress_row['actress_name'] # Duplicate
            
            # Fetch first genre for this video
            genre_list_for_template_cn = []
            genre_list_for_template_en = [] # Will be same as CN for now
            if row['video_id']:
                genre_cursor = conn.cursor(dictionary=True)
                video_genre_query = ("""
                    SELECT g.id AS genre_id, g.name AS genre_name
                    FROM genres g
                    JOIN video_genre vg ON g.id = vg.genre_id
                    WHERE vg.video_id = %s
                    LIMIT 1 
                """)
                genre_cursor.execute(video_genre_query, (row['video_id'],))
                genre_row = genre_cursor.fetchone()
                genre_cursor.close()
                if genre_row:
                    genre_file_id = generate_filename_component(str(genre_row['genre_id']))
                    genre_obj = {
                        "id": genre_row['genre_id'],
                        "name": genre_row['genre_name'], 
                        "url": Path(f"genres/{genre_file_id}_cn.html").as_posix() # Assuming _cn for now
                    }
                    genre_list_for_template_cn.append(genre_obj)
                    # For en version, use the same object as data is only in CN
                    genre_obj_en = {
                        "id": genre_row['genre_id'],
                        "name": genre_row['genre_name'], # Use CN name
                        "url": Path(f"genres/{genre_file_id}_en.html").as_posix()
                    }
                    genre_list_for_template_en.append(genre_obj_en)

            video_item = {
                "id": row['video_id'],
                "code": row['video_code'],
                "title_cn": row['video_title'],
                "title_en": row['video_title'], # Duplicate
                "actress_id": actress_id_val, # Store the actual ID
                "actress_name_cn": actress_name_for_template_cn,
                "actress_name_en": actress_name_for_template_en, 
                "actress_page_path_cn": Path(f"actresses/{actress_id_for_file}_cn.html"),
                "actress_page_path_en": Path(f"actresses/{actress_id_for_file}_en.html"),
                "genres_cn": genre_list_for_template_cn,
                "genres_en": genre_list_for_template_en, 
                "release_date": row['release_date'].strftime("%Y-%m-%d") if row['release_date'] else "N/A",
                "datetime_obj": row['release_date'].replace(tzinfo=timezone.utc) if row['release_date'] else datetime.min.replace(tzinfo=timezone.utc), # Ensure timezone for sort
                "summary_cn": (row['video_description'][:80] + "..." if row['video_description'] and len(row['video_description']) > 80 else row['video_description']) or "暫無簡介",
                "summary_en": (row['video_description'][:80] + "..." if row['video_description'] and len(row['video_description']) > 80 else row['video_description']) or "No description", # Duplicate
                "detail_page_path_cn": Path(f"videos/{video_file_code}_cn.html"),
                "detail_page_path_en": Path(f"videos/{video_file_code}_en.html"),
                "cover_url": row['cover_url'], 
            }
            videos_data.append(video_item)
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching latest videos: {err}")
        import traceback
        traceback.print_exc() # More detailed error for SQL issues
    finally:
        if conn and conn.is_connected():
            conn.close()
            
    # Sort in Python after all data is fetched and processed
    videos_data.sort(key=lambda v: v.get("datetime_obj", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return videos_data

def fetch_popular_items_from_db(item_type="genres", limit=NUM_POPULAR_GENRES_INDEX):
    real_limit = min(limit, TEST_LIMIT) if TEST_LIMIT else limit
    conn = get_db_connection()
    if not conn: return []
    
    items_data = []
    actual_limit = real_limit
    if item_type == "actresses": actual_limit = NUM_POPULAR_ACTRESSES_INDEX

    try:
        cursor = conn.cursor(dictionary=True)
        if item_type == "genres": 
            query = ("""
                SELECT g.id, g.name, COUNT(vg.video_id) as video_count
                FROM genres g
                LEFT JOIN video_genre vg ON g.id = vg.genre_id
                GROUP BY g.id, g.name 
                ORDER BY video_count DESC
                LIMIT %s
            """)
        elif item_type == "actresses":
            query = ("""
                SELECT act.id, act.name, COUNT(va.video_id) as video_count
                FROM actresses act
                LEFT JOIN video_actress va ON act.id = va.actress_id
                GROUP BY act.id, act.name
                ORDER BY video_count DESC
                LIMIT %s
            """)
        else:
            return []
            
        cursor.execute(query, (actual_limit,))
        for row in cursor.fetchall():
            item_file_id = generate_filename_component(str(row['id']))
            items_data.append({
                "id": row['id'],
                "name_cn": row['name'], 
                "name_en": row['name'], # Duplicate for now
                "video_count": row.get('video_count', 0),
                "page_path_cn": Path(f"{item_type}/{item_file_id}_cn.html"),
                "page_path_en": Path(f"{item_type}/{item_file_id}_en.html"),
            })
        cursor.close()
    except mysql.connector.Error as err:
        logging.error(f"Error fetching popular {item_type}: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return items_data

# --- 路徑輔助函數 --- (get_relative_static_paths - unchanged for now)
def get_relative_static_paths(output_html_rel_path: Path):
    html_file_parent_dir_abs = (OUTPUT_DIR / output_html_rel_path).parent.resolve()
    static_dir_abs = (OUTPUT_DIR / "static").resolve()
    relative_base_to_static_dir = Path(os.path.relpath(static_dir_abs, html_file_parent_dir_abs))
    paths = {
        "path_css": (relative_base_to_static_dir / "style.css").as_posix(),
        "path_favicon": (relative_base_to_static_dir / "favicon.png").as_posix(),
        "path_logo": (relative_base_to_static_dir / "LOGO.png").as_posix(),
        "path_ad_js": (relative_base_to_static_dir / "ad.js").as_posix(),
        "path_search_js": (relative_base_to_static_dir / "search.js").as_posix(),
        "path_path_resolver_js": (relative_base_to_static_dir / "path-resolver.js").as_posix(),
        "path_placeholder_thumb": (relative_base_to_static_dir / "placeholder_thumb.png").as_posix(),
        "path_placeholder_avatar": (relative_base_to_static_dir / "placeholder_avatar.png").as_posix(),
        "path_placeholder_og_video": (relative_base_to_static_dir / "placeholder_og_video.png").as_posix(),
        "path_placeholder_og_category": (relative_base_to_static_dir / "placeholder_og_category.png").as_posix(), # Should be og_genre now
        "path_placeholder_og_actress": (relative_base_to_static_dir / "placeholder_og_actress.png").as_posix(),
    }
    return paths

# --- HTML Rendering Function ---
def write_html(output_rel_path: Path, template_name: str, context: dict):
    template = jinja_env.get_template(template_name)
    lang = context.get("lang", "en")
    static_paths_map = get_relative_static_paths(output_rel_path)
    context.update(static_paths_map) # Add all static paths to context

    # Process single video (for detail page) - fields are mostly from DB or derived
    if "video" in context and isinstance(context["video"], dict):
        video = context["video"]
        video["title_display"] = video.get(f"title_{lang}", "N/A")
        video["actress_name_display"] = video.get(f"actress_name_{lang}", "未知")
        actress_page_path = video.get(f"actress_page_path_{lang}")
        video["actress_url"] = actress_page_path.as_posix() if isinstance(actress_page_path, Path) else "#"
        
        video["genres_for_template"] = video.get(f"genres_{lang}", []) 
        video["tags_for_template"] = [] # Tags not implemented from DB yet
        video["review_display"] = video.get(f"review_{lang}", "") # Assuming review field in DB for detail
        video["plot_summary_display"] = video.get(f"description", "") # Use description for plot

        # Cover images: use direct cover_url if available, else placeholder
        video["cover_image_url_clear"] = video.get("cover_url") or static_paths_map["path_placeholder_thumb"]
        # For detail page, blurred can be same as clear if no separate blurred image logic yet
        video["cover_image_url_blurred"] = video.get("cover_url") or static_paths_map["path_placeholder_thumb"]

    # Process single category (genre) (for genre page)
    if "category" in context and isinstance(context["category"], dict): # Keep 'category' key for now, maps to genre
        genre_data = context["category"] # conceptually this is a genre
        genre_data["name_display"] = genre_data.get(f"name_{lang}", "N/A")
        genre_data["description_display"] = genre_data.get(f"description_{lang}", "") # if genres have descriptions
        # genre_data["image_url"] = ... if genres have specific OG images

    # Process single actress (for actress page)
    if "actress" in context and isinstance(context["actress"], dict):
        actress_data = context["actress"]
        actress_data["name_display"] = actress_data.get(f"name_{lang}", "N/A")
        # actress_data["bio_display"] = ... if actresses have bio
        # actress_data["profile_image_url"] = ... 
        # actress_data["popular_tags_display"] = []

    # Process video lists (for index, genre, actress pages)
    for video_list_key in ["latest_videos", "videos_in_category", "videos_by_actress"]:
        if video_list_key in context and isinstance(context[video_list_key], list):
            for video_item in context[video_list_key]:
                if not isinstance(video_item, dict): continue

                video_item["title_display"] = video_item.get(f"title_{lang}", "N/A")
                video_item["actress_name_display"] = video_item.get(f"actress_name_{lang}", "未知")
                video_item["summary_display"] = video_item.get(f"summary_{lang}", "")
                
                detail_page_path = video_item.get(f"detail_page_path_{lang}")
                video_item["detail_url"] = detail_page_path.as_posix() if isinstance(detail_page_path, Path) else "#"
                
                actress_page_path_item = video_item.get(f"actress_page_path_{lang}")
                video_item["actress_url"] = actress_page_path_item.as_posix() if isinstance(actress_page_path_item, Path) else "#"

                video_item["cover_thumbnail_url"] = video_item.get("cover_url") or static_paths_map["path_placeholder_thumb"]
                video_item["genres_for_template"] = video_item.get(f"genres_{lang}", [])
                video_item["fanhao"] = video_item.get("code", "CODE-N/A") # For display on card if needed

    current_page_name = output_rel_path.name
    if lang == "cn":
        alt_page_name = current_page_name.replace("_cn.html", "_en.html")
    else:
        alt_page_name = current_page_name.replace("_en.html", "_cn.html")
    context["alternate_lang_url"] = alt_page_name 
    context["current_page_url"] = output_rel_path.as_posix()
    # Static paths already added

    full_output_path = OUTPUT_DIR / output_rel_path
    full_output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        rendered_html = template.render(context)
        with open(full_output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        logging.info(f"Generated: {output_rel_path.as_posix()}")
    except Exception as e:
        logging.error(f"Error rendering {template_name} for {output_rel_path.as_posix()}: {e}")
        import traceback
        traceback.print_exc()


# --- 頁面生成函數 ---
def generate_index_pages():
    # 取得所有影片（受 TEST_LIMIT 控制）
    all_videos = fetch_latest_videos_for_index(limit=TEST_LIMIT)
    total_videos = len(all_videos)
    total_pages = max(1, (total_videos + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)

    # 精選推薦（隨機或熱門）
    import random
    featured_videos = random.sample(all_videos, min(FEATURED_COUNT, total_videos)) if total_videos >= FEATURED_COUNT else all_videos[:FEATURED_COUNT]
    # 熱門 chips
    hot_genres = fetch_popular_items_from_db(item_type="genres", limit=8)
    hot_actresses = fetch_popular_items_from_db(item_type="actresses", limit=8)
    # 熱門排行榜（先隨機）
    hot_rank_videos = random.sample(all_videos, min(HOT_RANK_COUNT, total_videos)) if total_videos >= HOT_RANK_COUNT else all_videos[:HOT_RANK_COUNT]

    # 分頁產生
    for page in range(1, total_pages+1):
        start_idx = (page-1)*VIDEOS_PER_PAGE
        end_idx = start_idx + VIDEOS_PER_PAGE
        videos_for_page = all_videos[start_idx:end_idx]
        page_urls = [f"index_p{p}.html" for p in range(1, total_pages+1)]
        context_pages = {
            "lang": "cn",  # 預設中文，英文分頁可依需求擴展
            "featured_videos": featured_videos,
            "hot_genres": hot_genres,
            "hot_actresses": hot_actresses,
            "hot_rank_videos": hot_rank_videos,
            "latest_videos": videos_for_page,
            "current_page": page,
            "total_pages": total_pages,
            "page_urls": page_urls,
            "nav_all_categories_url": "genres_overview_cn.html",
            "nav_all_actresses_url": "actresses_overview_cn.html",
            "nav_all_series_url": "series_overview_cn.html",
            "nav_all_labels_url": "labels_overview_cn.html",
            "nav_disclaimer_url": "disclaimer_cn.html",
            "seo": {
                "title_cn": f"Fanhao Diary - 我的深夜觀影手記 第{page}頁",
                "meta_description_cn": "歡迎來到Fanhao Diary，精選推薦、熱門分類、女優、排行榜與最新影片分頁。"
            }
        }
        page_path_html = Path(f"index_p{page}.html")
        write_html(page_path_html, "index_static.html", context_pages)
        # 產生首頁 alias
        if page == 1:
            write_html(Path("index.html"), "index_static.html", context_pages)

def format_review_with_paragraphs(review_text):
    """将评论文本自动分段，每2-3句成为一个段落"""
    if not review_text:
        return ""
    
    # 定义句子结束标记
    sentence_endings = ['.', '。', '!', '！', '?', '？']
    
    # 将文本按照句子分割
    sentences = []
    current_sentence = ""
    
    for char in review_text:
        current_sentence += char
        if char in sentence_endings:
            sentences.append(current_sentence.strip())
            current_sentence = ""
    
    # 处理最后一个可能没有结束标记的句子
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
    
    # 每2-3句组成一个段落
    paragraphs = []
    current_paragraph = []
    sentences_per_paragraph = 2  # 默认每段2句
    
    for i, sentence in enumerate(sentences):
        current_paragraph.append(sentence)
        
        # 如果达到了每段句子数，或者是最后一句
        if (i + 1) % sentences_per_paragraph == 0 or i == len(sentences) - 1:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []
    
    # 处理可能剩余的句子
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))
    
    # 用<p>标签包裹每个段落
    return "\n".join([f"<p>{p}</p>" for p in paragraphs])

def fetch_video_details_from_db(video_identifier): # identifier can be id or code
    conn = get_db_connection()
    if not conn:
        return None
    
    video_details = {}
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Determine if identifier is an ID (int) or code (string)
        is_code = isinstance(video_identifier, str)
        
        # Main query for video details
        if is_code:
            video_query = """
                SELECT v.*
                FROM videos v
                WHERE v.code = %s
                LIMIT 1
            """
        else:
            video_query = """
                SELECT v.*
                FROM videos v
                WHERE v.id = %s
                LIMIT 1
            """
        
        cursor.execute(video_query, (video_identifier,))
        row = cursor.fetchone()
        
        if not row:
            logging.warning(f"No video found for identifier: {video_identifier}")
            return None
        
        # 設置預設值，因為ai_reviews表不存在
        review_cn = "<p>暫時還沒有觀影心得，很快就會更新哦！</p>"
        review_en = "<p>Review coming soon, stay tuned!</p>"
        plot_summary_cn = "<p>劇情簡介即將推出，敬請期待！</p>"
        plot_summary_en = "<p>Plot summary will be available soon!</p>"
        
        # Basic video info
        video_details = {
            'id': row['id'],
            'code': row['code'],
            'title_cn': row['title'] or f"{row['code']} - 未知標題",
            'title_en': row['title'] or f"{row['code']} - Unknown Title", # Placeholder for future translation
            'release_date': row['release_date'].strftime('%Y-%m-%d') if row['release_date'] else 'Unknown',
            'cover_image_url': row['cover_url'] or '',
            'cover_image_url_blurred': row['cover_url'] or '', # In this phase, no blur processing
            'cover_image_url_clear': row['cover_url'] or '',
            'review_cn': review_cn,
            'review_en': review_en,
            'plot_summary_cn': plot_summary_cn,
            'plot_summary_en': plot_summary_en,
            'description': row.get('description', ''),
        }
        
        # Temporary hard-coded placeholders for when no AI review data
        if not video_details['review_cn']:
            video_details['review_cn'] = "<p>暫時還沒有觀影心得，很快就會更新哦！</p>"
        if not video_details['review_en']:
            video_details['review_en'] = "<p>Review coming soon, stay tuned!</p>"
        if not video_details['plot_summary_cn']:
            video_details['plot_summary_cn'] = "<p>劇情簡介即將推出，敬請期待！</p>"
        if not video_details['plot_summary_en']:
            video_details['plot_summary_en'] = "<p>Plot summary will be available soon!</p>"

        # Fetch actresses
        actress_query = """
            SELECT act.id, act.name
            FROM actresses act
            JOIN video_actress va ON act.id = va.actress_id
            WHERE va.video_id = %s
            ORDER BY act.name
        """
        cursor.execute(actress_query, (video_details['id'],))
        actresses = []
        actress_file_id_prefix = "actresses"
        for act_row in cursor.fetchall():
            act_file_id = generate_filename_component(str(act_row['id']))
            actresses.append({
                "id": act_row['id'],
                "name_cn": act_row['name'],
                "name_en": act_row['name'], # Duplicate
                "page_path_cn": Path(f"{actress_file_id_prefix}/{act_file_id}_cn.html"),
                "page_path_en": Path(f"{actress_file_id_prefix}/{act_file_id}_en.html"),
            })
        video_details['actresses_cn'] = actresses # Changed key to actresses_cn for write_html compatibility
        video_details['actresses_en'] = actresses 

        # Set primary actress info for direct access in template if needed
        if actresses:
            primary_actress = actresses[0] # Take the first one as primary
            video_details['actress_name_cn'] = primary_actress['name_cn']
            video_details['actress_name_en'] = primary_actress['name_en']
            # Ensure these are Path objects as original logic in write_html might expect Path then convert to str
            video_details['actress_page_path_cn'] = primary_actress['page_path_cn'] 
            video_details['actress_page_path_en'] = primary_actress['page_path_en'] 
        else:
            video_details['actress_name_cn'] = "未知女優"
            video_details['actress_name_en'] = "Unknown Actress"
            video_details['actress_page_path_cn'] = Path("#") # Use Path for consistency
            video_details['actress_page_path_en'] = Path("#")

        # Fetch genres (categories)
        genre_query = """
            SELECT g.id, g.name
            FROM genres g
            JOIN video_genre vg ON g.id = vg.genre_id
            WHERE vg.video_id = %s
            ORDER BY g.name
        """
        cursor.execute(genre_query, (video_details['id'],))
        genres = []
        genre_file_id_prefix = "genres"
        for gen_row in cursor.fetchall():
            gen_file_id = generate_filename_component(str(gen_row['id']))
            genres.append({
                "id": gen_row['id'],
                "name_cn": gen_row['name'],
                "name_en": gen_row['name'], # Duplicate
                "page_path_cn": Path(f"{genre_file_id_prefix}/{gen_file_id}_cn.html"),
                "page_path_en": Path(f"{genre_file_id_prefix}/{gen_file_id}_en.html"),
            })
        video_details['genres_cn'] = genres # Changed key to genres_cn for write_html compatibility
        video_details['genres_en'] = genres 

        # Set primary genre info (e.g., for breadcrumbs or simple display if needed)
        if genres:
            primary_genre = genres[0]
            video_details['primary_genre_id'] = primary_genre['id']
            video_details['primary_genre_name_cn'] = primary_genre['name_cn']
            video_details['primary_genre_name_en'] = primary_genre['name_en']
            video_details['primary_genre_page_path_cn'] = primary_genre['page_path_cn']
            video_details['primary_genre_page_path_en'] = primary_genre['page_path_en']
        else:
            video_details['primary_genre_id'] = None
            video_details['primary_genre_name_cn'] = "未分類"
            video_details['primary_genre_name_en'] = "Uncategorized"
            video_details['primary_genre_page_path_cn'] = Path("#")
            video_details['primary_genre_page_path_en'] = Path("#")

        # Fetch Series
        series_list = []
        series_query = """
            SELECT s.id, s.name 
            FROM series s
            JOIN video_series vs ON s.id = vs.series_id
            WHERE vs.video_id = %s
            ORDER BY s.name
        """
        cursor.execute(series_query, (video_details['id'],))
        series_file_id_prefix = "series" # Assuming series will have their own pages eventually
        for series_row in cursor.fetchall():
            series_file_id = generate_filename_component(str(series_row['id']))
            series_list.append({
                "id": series_row['id'],
                "name_cn": series_row['name'],
                "name_en": series_row['name'], # Duplicate
                # "page_path_cn": Path(f"{series_file_id_prefix}/{series_file_id}_cn.html"), # If series pages exist
                # "page_path_en": Path(f"{series_file_id_prefix}/{series_file_id}_en.html"),
            })
        video_details['series_list_cn'] = series_list
        video_details['series_list_en'] = series_list

        # Fetch Labels
        labels_list = []
        labels_query = """
            SELECT l.id, l.name
            FROM labels l
            JOIN video_label vl ON l.id = vl.label_id
            WHERE vl.video_id = %s
            ORDER BY l.name
        """
        cursor.execute(labels_query, (video_details['id'],))
        label_file_id_prefix = "labels" # Assuming labels will have their own pages eventually
        for label_row in cursor.fetchall():
            label_file_id = generate_filename_component(str(label_row['id']))
            labels_list.append({
                "id": label_row['id'],
                "name_cn": label_row['name'],
                "name_en": label_row['name'], # Duplicate
                # "page_path_cn": Path(f"{label_file_id_prefix}/{label_file_id}_cn.html"), # If label pages exist
                # "page_path_en": Path(f"{label_file_id_prefix}/{label_file_id}_en.html"),
            })
        video_details['labels_list_cn'] = labels_list
        video_details['labels_list_en'] = labels_list
        
        # Fetch Actors (Male Actors)
        actors_list = []
        actors_query = """
            SELECT ac.id, ac.name  -- Changed from 'actors' to 'ac' to avoid conflict if table was named 'actors'
            FROM actors ac  -- Assuming the table is named 'actors'
            JOIN video_actor va ON ac.id = va.actor_id -- Assuming join table is 'video_actor' and foreign key 'actor_id'
            WHERE va.video_id = %s
            ORDER BY ac.name
        """
        # This query assumes table names 'actors', 'video_actor'. Adjust if different.
        try:
            cursor.execute(actors_query, (video_details['id'],))
            actor_file_id_prefix = "actors" 
            for actor_row in cursor.fetchall():
                actor_file_id = generate_filename_component(str(actor_row['id']))
                actors_list.append({
                    "id": actor_row['id'],
                    "name_cn": actor_row['name'],
                    "name_en": actor_row['name'],
                    # "page_path_cn": Path(f"{actor_file_id_prefix}/{actor_file_id}_cn.html"), 
                    # "page_path_en": Path(f"{actor_file_id_prefix}/{actor_file_id}_en.html"),
                })
        except mysql.connector.Error as actor_err:
            # If 'actors' table or related tables don't exist, log and continue
            logging.warning(f"Could not fetch actors for video {video_details['id']}: {actor_err}. Actors list will be empty.")
            pass # Non-critical, so continue
            
        video_details['actors_list_cn'] = actors_list
        video_details['actors_list_en'] = actors_list


        video_details['title_cn'] = video_details.get('title')
        video_details['title_en'] = video_details.get('title') 
        video_details['description_cn'] = video_details.get('description')
        video_details['description_en'] = video_details.get('description') 
        
        video_details['release_date_str'] = video_details['release_date'].strftime("%Y-%m-%d") if video_details.get('release_date') else "N/A"
        video_details['duration_str'] = str(timedelta(seconds=video_details['duration'])) if video_details.get('duration') else "N/A"
        
        video_file_code = generate_filename_component(video_details['code'] if video_details.get('code') else str(video_details['id']))
        video_details['detail_page_path_cn'] = Path(f"videos/{video_file_code}_cn.html")
        video_details['detail_page_path_en'] = Path(f"videos/{video_file_code}_en.html")

        # 新增摘要 summary_cn/summary_en，供模板 SEO 用
        video_details['summary_cn'] = (video_details['description_cn'][:80] + "..." if video_details.get('description_cn') and len(video_details['description_cn']) > 80 else video_details.get('description_cn')) or "暫無簡介"
        video_details['summary_en'] = (video_details['description_en'][:80] + "..." if video_details.get('description_en') and len(video_details['description_en']) > 80 else video_details.get('description_en')) or "No description"

        cursor.close()

    except mysql.connector.Error as err:
        logging.error(f"Error fetching video details for '{video_identifier}': {err}")
        import traceback
        traceback.print_exc()
        if cursor and not cursor._have_result: cursor.close() # 修改檢查方式
        return None 
    except Exception as e: 
        logging.error(f"An unexpected error occurred fetching video details for '{video_identifier}': {e}")
        import traceback
        traceback.print_exc()
        if cursor and not cursor._have_result: cursor.close() # 修改檢查方式
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()
            
    return video_details

# --- New function to fetch genre details and its videos ---
def fetch_genre_details_and_videos(genre_id):
    conn = get_db_connection()
    if not conn:
        return None

    genre_details = {}
    videos_in_genre = []

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch genre details
        genre_query = "SELECT id, name FROM genres WHERE id = %s"
        cursor.execute(genre_query, (genre_id,))
        genre_data = cursor.fetchone()

        if not genre_data:
            logging.warning(f"Genre with ID '{genre_id}' not found.")
            cursor.close()
            return None

        genre_details["id"] = genre_data["id"]
        genre_details["name_cn"] = genre_data["name"]
        genre_details["name_en"] = genre_data["name"] # Duplicate for now
        # Assuming no description field in 'genres' table as per schema
        genre_details["description_cn"] = "" 
        genre_details["description_en"] = ""
        
        genre_file_component = generate_filename_component(str(genre_data["id"]))
        genre_details["page_path_cn"] = Path(f"genres/{genre_file_component}_cn.html")
        genre_details["page_path_en"] = Path(f"genres/{genre_file_component}_en.html")

        # 2. Fetch videos for this genre
        videos_query = """
            SELECT 
                v.id AS video_id, v.code AS video_code, v.title AS video_title, 
                v.release_date, v.description AS video_description,
                v.cover_url, v.created_at
            FROM videos v
            JOIN video_genre vg ON v.id = vg.video_id
            WHERE vg.genre_id = %s
            ORDER BY v.release_date DESC, v.created_at DESC
            LIMIT %s
        """
        real_limit = TEST_LIMIT if TEST_LIMIT else 10000
        cursor.execute(videos_query, (genre_id, real_limit))
        raw_videos = cursor.fetchall()
        
        # Close main cursor for genre and videos before opening new ones in loop
        cursor.close()


        for row in raw_videos:
            video_file_code = generate_filename_component(row['video_code'] if row['video_code'] else str(row['video_id']))
            
            # Fetch first actress for this video (similar to fetch_latest_videos_for_index)
            actress_id_for_file = "unknown-actress"
            actress_name_for_template_cn = "未知女優"
            actress_name_for_template_en = "Unknown Actress"
            actress_id_val = None

            if row['video_id']:
                # Need a new cursor for this sub-query
                actress_conn = get_db_connection() # Or reuse conn if careful about cursor management
                if not actress_conn: continue # Skip actress if connection fails
                
                actress_cursor = actress_conn.cursor(dictionary=True)
                video_actress_query = """
                    SELECT act.id AS actress_id, act.name AS actress_name
                    FROM actresses act
                    JOIN video_actress va ON act.id = va.actress_id
                    WHERE va.video_id = %s
                    LIMIT 1
                """
                actress_cursor.execute(video_actress_query, (row['video_id'],))
                actress_row = actress_cursor.fetchone()
                actress_cursor.close()
                if actress_conn.is_connected(): actress_conn.close()

                if actress_row:
                    actress_id_val = actress_row['actress_id']
                    actress_id_for_file = generate_filename_component(str(actress_row['actress_id']))
                    actress_name_for_template_cn = actress_row['actress_name']
                    actress_name_for_template_en = actress_row['actress_name']
            
            # For videos listed on a genre page, they might not need their own genre list displayed on the card.
            # Or, if they do (e.g. if a video has multiple genres), this would need fetching.
            # For now, keeping it simple: genre list on card is empty or not primary focus here.
            genre_list_for_video_card_cn = []
            genre_list_for_video_card_en = []

            video_item = {
                "id": row['video_id'],
                "code": row['video_code'],
                "title_cn": row['video_title'],
                "title_en": row['video_title'],
                "actress_id": actress_id_val,
                "actress_name_cn": actress_name_for_template_cn,
                "actress_name_en": actress_name_for_template_en,
                "actress_page_path_cn": Path(f"actresses/{actress_id_for_file}_cn.html"),
                "actress_page_path_en": Path(f"actresses/{actress_id_for_file}_en.html"),
                "genres_cn": genre_list_for_video_card_cn, # Videos on a genre page, their own genre list on card is less critical
                "genres_en": genre_list_for_video_card_en,
                "release_date": row['release_date'].strftime("%Y-%m-%d") if row['release_date'] else "N/A",
                "datetime_obj": row['release_date'].replace(tzinfo=timezone.utc) if row['release_date'] else datetime.min.replace(tzinfo=timezone.utc),
                "summary_cn": (row['video_description'][:80] + "..." if row['video_description'] and len(row['video_description']) > 80 else row['video_description']) or "暫無簡介",
                "summary_en": (row['video_description'][:80] + "..." if row['video_description'] and len(row['video_description']) > 80 else row['video_description']) or "No description",
                "detail_page_path_cn": Path(f"videos/{video_file_code}_cn.html"),
                "detail_page_path_en": Path(f"videos/{video_file_code}_en.html"),
                "cover_url": row['cover_url'],
            }
            videos_in_genre.append(video_item)
        
        genre_details["videos_in_genre"] = videos_in_genre
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching details for genre ID '{genre_id}': {err}")
        import traceback
        traceback.print_exc()
        # Ensure cursor is closed if it was opened and an error occurred before its explicit close
        if 'cursor' in locals() and cursor and not cursor._have_result:
            cursor.close()
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred fetching genre details for ID '{genre_id}': {e}")
        import traceback
        traceback.print_exc()
        if 'cursor' in locals() and cursor and not cursor._have_result:
            cursor.close()
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()
            
    return genre_details

# --- New function to fetch actress details and her videos ---
def fetch_actress_details_and_videos(actress_id):
    conn = get_db_connection()
    if not conn:
        return None

    actress_details = {}
    videos_by_actress = []

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch actress details
        actress_query_main = "SELECT id, name FROM actresses WHERE id = %s"
        cursor.execute(actress_query_main, (actress_id,))
        actress_data = cursor.fetchone()

        if not actress_data:
            logging.warning(f"Actress with ID '{actress_id}' not found.")
            cursor.close()
            return None

        actress_details["id"] = actress_data["id"]
        actress_details["name_cn"] = actress_data["name"]
        actress_details["name_en"] = actress_data["name"] # Duplicate for now
        # Assuming no bio or profile_image_filename in 'actresses' table as per schema
        actress_details["bio_cn"] = "" 
        actress_details["bio_en"] = ""
        actress_details["profile_image_url"] = "" # Placeholder
        actress_details["popular_tags_display"] = [] # Placeholder, not in DB

        actress_file_component = generate_filename_component(str(actress_data["id"]))
        actress_details["page_path_cn"] = Path(f"actresses/{actress_file_component}_cn.html")
        actress_details["page_path_en"] = Path(f"actresses/{actress_file_component}_en.html")

        # 2. Fetch videos by this actress
        videos_query = """
            SELECT 
                v.id AS video_id, v.code AS video_code, v.title AS video_title, 
                v.release_date, v.description AS video_description,
                v.cover_url, v.created_at
            FROM videos v
            JOIN video_actress va ON v.id = va.video_id
            WHERE va.actress_id = %s
            ORDER BY v.release_date DESC, v.created_at DESC
        """
        cursor.execute(videos_query, (actress_id,))
        raw_videos = cursor.fetchall()
        cursor.close() # Close main cursor

        for row in raw_videos:
            video_file_code = generate_filename_component(row['video_code'] if row['video_code'] else str(row['video_id']))
            
            # Fetch first genre for this video card
            genre_list_for_video_card_cn = []
            genre_list_for_video_card_en = []
            primary_genre_name_cn = "未分類"
            primary_genre_name_en = "Uncategorized"
            genre_id_val = None

            if row['video_id']:
                genre_conn = get_db_connection()
                if not genre_conn: continue
                genre_cursor = genre_conn.cursor(dictionary=True)
                video_genre_query = """
                    SELECT g.id AS genre_id, g.name AS genre_name
                    FROM genres g
                    JOIN video_genre vg ON g.id = vg.genre_id
                    WHERE vg.video_id = %s
                    LIMIT 1 
                """
                genre_cursor.execute(video_genre_query, (row['video_id'],))
                genre_row = genre_cursor.fetchone()
                genre_cursor.close()
                if genre_conn.is_connected(): genre_conn.close()

                if genre_row:
                    genre_id_val = genre_row['genre_id']
                    genre_file_id = generate_filename_component(str(genre_row['genre_id']))
                    primary_genre_name_cn = genre_row['genre_name']
                    primary_genre_name_en = genre_row['genre_name'] # Duplicate
                    genre_obj = {
                        "id": genre_row['genre_id'],
                        "name": genre_row['genre_name'], 
                        "url": Path(f"genres/{genre_file_id}_cn.html").as_posix()
                    }
                    genre_list_for_video_card_cn.append(genre_obj)
                    genre_obj_en = {
                        "id": genre_row['genre_id'],
                        "name": genre_row['genre_name'], 
                        "url": Path(f"genres/{genre_file_id}_en.html").as_posix()
                    }
                    genre_list_for_video_card_en.append(genre_obj_en)

            video_item = {
                "id": row['video_id'],
                "code": row['video_code'],
                "title_cn": row['video_title'],
                "title_en": row['video_title'],
                # For videos on an actress page, the actress name on card is redundant.
                # Instead, we might show primary genre or keep it clean.
                "actress_id": actress_details['id'], # The current actress of the page
                "actress_name_cn": actress_details['name_cn'],
                "actress_name_en": actress_details['name_en'],
                "actress_page_path_cn": actress_details['page_path_cn'],
                "actress_page_path_en": actress_details['page_path_en'],
                
                "genres_cn": genre_list_for_video_card_cn, 
                "genres_en": genre_list_for_video_card_en,
                "primary_genre_name_cn": primary_genre_name_cn, # For display if needed
                "primary_genre_name_en": primary_genre_name_en,

                "release_date": row['release_date'].strftime("%Y-%m-%d") if row['release_date'] else "N/A",
                "datetime_obj": row['release_date'].replace(tzinfo=timezone.utc) if row['release_date'] else datetime.min.replace(tzinfo=timezone.utc),
                "summary_cn": (row['video_description'][:80] + "..." if row['video_description'] and len(row['video_description']) > 80 else row['video_description']) or "暫無簡介",
                "summary_en": (row['video_description'][:80] + "..." if row['video_description'] and len(row['video_description']) > 80 else row['video_description']) or "No description",
                "detail_page_path_cn": Path(f"videos/{video_file_code}_cn.html"),
                "detail_page_path_en": Path(f"videos/{video_file_code}_en.html"),
                "cover_url": row['cover_url'],
            }
            videos_by_actress.append(video_item)
        
        actress_details["videos_by_actress"] = videos_by_actress
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching details for actress ID '{actress_id}': {err}")
        import traceback; traceback.print_exc()
        if 'cursor' in locals() and cursor and not cursor._have_result: cursor.close()
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred fetching actress details for ID '{actress_id}': {e}")
        import traceback; traceback.print_exc()
        if 'cursor' in locals() and cursor and not cursor._have_result: cursor.close()
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()
            
    return actress_details

# --- New function to fetch all items (genres/actresses) for overview pages ---
def fetch_all_items_for_overview(item_type="genres"):
    real_limit = TEST_LIMIT if TEST_LIMIT else None
    conn = get_db_connection()
    if not conn: 
        return []
    
    items_data = []
    try:
        cursor = conn.cursor(dictionary=True)
        if item_type == "genres": 
            query = ("""
                SELECT g.id, g.name, COUNT(vg.video_id) as video_count
                FROM genres g
                LEFT JOIN video_genre vg ON g.id = vg.genre_id
                GROUP BY g.id, g.name 
                ORDER BY g.name ASC
            """ + (f" LIMIT {real_limit}" if real_limit else ""))
        elif item_type == "actresses":
            query = ("""
                SELECT act.id, act.name, COUNT(va.video_id) as video_count
                FROM actresses act
                LEFT JOIN video_actress va ON act.id = va.actress_id
                GROUP BY act.id, act.name
                ORDER BY act.name ASC
            """ + (f" LIMIT {real_limit}" if real_limit else ""))
        else:
            logging.error(f"Unsupported item_type for overview: {item_type}")
            return []
        cursor.execute(query)
        for row in cursor.fetchall():
            item_file_id = generate_filename_component(str(row['id']))
            items_data.append({
                "id": row['id'],
                "name_cn": row['name'], 
                "name_en": row['name'], # Duplicate for now
                "video_count": row.get('video_count', 0),
                # These page paths point to individual genre/actress pages
                "page_path_cn": Path(f"{item_type}/{item_file_id}_cn.html"),
                "page_path_en": Path(f"{item_type}/{item_file_id}_en.html"),
            })
        cursor.close()
    except mysql.connector.Error as err:
        logging.error(f"Error fetching all {item_type} for overview: {err}")
        import traceback; traceback.print_exc()
    finally:
        if conn and conn.is_connected():
            conn.close()
    return items_data


# --- Functions for other pages (to be updated for DB later) ---
def generate_detail_pages():
    conn = get_db_connection()
    if not conn:
        logging.error("Cannot generate detail pages: DB connection failed.")
        return

    all_video_identifiers = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, code FROM videos") 
        for row in cursor.fetchall():
            all_video_identifiers.append(row['code'] if row['code'] else str(row['id']))
        cursor.close()
    except mysql.connector.Error as err:
        logging.error(f"Error fetching video identifiers for detail pages: {err}")
        if conn and conn.is_connected(): conn.close()
        return
    # Removed redundant finally block for conn.close() as it's handled by the main try/finally of this function now.
    # Ensure connection used for fetching identifiers is closed before entering loop.
    if conn and conn.is_connected(): # Close after fetching identifiers
        conn.close()


    if not all_video_identifiers:
        logging.info("No videos found in DB to generate detail pages for.")
        return
    
    logging.info(f"Starting generation of {len(all_video_identifiers)} video detail pages...")
    
    # 僅生成前5個影片作為測試，減少錯誤和時間消耗
    test_limit = 5
    if test_limit:
        logging.info(f"TEST MODE: Only generating {test_limit} video detail pages for testing.")
        all_video_identifiers = all_video_identifiers[:test_limit]

    for video_identifier in all_video_identifiers:
        try:
            video_data = fetch_video_details_from_db(video_identifier) # This function now handles its own DB connection
            if not video_data:
                logging.warning(f"Could not fetch details for video: {video_identifier}. Skipping page generation.")
                continue

            for lang in ["cn", "en"]:
                page_path_obj = video_data.get(f'detail_page_path_{lang}')
                if not page_path_obj: 
                    logging.error(f"Detail page path not found for video {video_identifier}, lang {lang}")
                    continue
                
                output_rel_path = page_path_obj

                context = {
                    "lang": lang,
                    "video": video_data, 
                    "seo": {
                        "title_cn": f"{video_data.get('title_cn', '影片詳情')} - {video_data.get('code', '')} | MOMO Fanhao Diary",
                        "meta_description_cn": (video_data.get('description_cn', '')[:157] + '...') if video_data.get('description_cn') and len(video_data.get('description_cn', '')) > 160 else video_data.get('description_cn', ''),
                        "title_en": f"{video_data.get('title_en', 'Video Details')} - {video_data.get('code', '')} | MOMO Fanhao Diary",
                        "meta_description_en": (video_data.get('description_en', '')[:157] + '...') if video_data.get('description_en') and len(video_data.get('description_en', '')) > 160 else video_data.get('description_en', ''),
                    },
                    "nav_home_url": f"../../index_{lang}.html", # Relative from videos/id_lang.html to output/index_lang.html
                    "nav_all_genres_url": f"../genres_overview_{lang}.html", 
                    "nav_all_actresses_url": f"../actresses_overview_{lang}.html", 
                    "nav_disclaimer_url": f"../disclaimer_{lang}.html" 
                }
                
                # OG image logic (handled by template or write_html's static_paths)
                # context["seo"]["og_image_url"] = video_data.get("cover_url") # or placeholder if not available

                write_html(output_rel_path, "detail_static.html", context)
        except Exception as e:
            logging.error(f"Error generating detail page for video {video_identifier}: {e}")
            import traceback
            traceback.print_exc()
            continue

def generate_genre_pages(): # Was generate_category_pages
    # logging.info("Skipping genre pages generation in this phase.")
    # Placeholder: Will need fetch_videos_for_category_from_db(category_slug)
    # pass
    conn = get_db_connection()
    if not conn:
        logging.error("Cannot generate genre pages: DB connection failed.")
        return

    all_genres_info = []
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch all genre IDs and names
        cursor.execute("SELECT id, name FROM genres ORDER BY name") 
        all_genres_info = cursor.fetchall()
        cursor.close()
    except mysql.connector.Error as err:
        logging.error(f"Error fetching genre list for pages: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()

    if not all_genres_info:
        logging.info("No genres found in DB to generate pages for.")
        return
    
    logging.info(f"Starting generation of {len(all_genres_info)} genre pages...")
    
    # 僅生成前5個類別作為測試
    test_limit = 5
    if test_limit:
        logging.info(f"TEST MODE: Only generating {test_limit} genre pages for testing.")
        all_genres_info = all_genres_info[:test_limit]

    for genre_info_row in all_genres_info:
        try:
            genre_id = genre_info_row['id']
            genre_name_for_seo = genre_info_row['name'] # Original name for SEO title
            
            genre_page_data = fetch_genre_details_and_videos(genre_id) 

            if not genre_page_data:
                logging.warning(f"Could not fetch details for genre ID: {genre_id}. Skipping page generation.")
                continue

            videos = genre_page_data.get("videos_in_genre", [])
            total_videos = len(videos)
            total_pages = max(1, (total_videos + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)

            for lang in ["cn", "en"]:
                for page in range(1, total_pages+1):
                    start_idx = (page-1)*VIDEOS_PER_PAGE
                    end_idx = start_idx + VIDEOS_PER_PAGE
                    videos_for_page = videos[start_idx:end_idx]
                    page_urls = [f"{genre_page_data['page_path_'+lang].stem}_p{p}.{genre_page_data['page_path_'+lang].suffix[1:]}" for p in range(1, total_pages+1)]
                    output_rel_path = Path(f"genres/{genre_page_data['page_path_'+lang].stem}_p{page}.{genre_page_data['page_path_'+lang].suffix[1:]}")
                    if page == 1:
                        output_rel_path = genre_page_data['page_path_'+lang]
                    category_for_template = {
                        "id": genre_page_data["id"],
                        "name_cn": genre_page_data["name_cn"],
                        "name_en": genre_page_data["name_en"],
                        "description_cn": genre_page_data["description_cn"],
                        "description_en": genre_page_data["description_en"],
                    }
                    context = {
                        "lang": lang,
                        "category": category_for_template, 
                        "videos_in_category": videos_for_page,
                        "current_page": page,
                        "total_pages": total_pages,
                        "page_urls": page_urls,
                        "seo": {
                            "title_cn": f"{genre_name_for_seo}分類影片 | MOMO Fanhao Diary 第{page}頁",
                            "meta_description_cn": f"探索 {genre_name_for_seo} 分類下的所有影片和心得。",
                            "title_en": f"{genre_name_for_seo} Genre Videos | MOMO Fanhao Diary Page {page}",
                            "meta_description_en": f"Explore all videos and reviews under the {genre_name_for_seo} genre.",
                        },
                        "nav_home_url": f"../index_{lang}.html", 
                        "nav_all_genres_url": f"../genres_overview_{lang}.html", 
                        "nav_all_actresses_url": f"../actresses_overview_{lang}.html", 
                        "nav_disclaimer_url": f"../disclaimer_{lang}.html"
                    }
                    write_html(output_rel_path, "category_static.html", context)
        except Exception as e:
            logging.error(f"Error generating page for genre {genre_info_row.get('name', genre_id)}: {e}")
            import traceback
            traceback.print_exc()
            continue

def generate_actress_pages():
    # logging.info("Skipping actress pages generation in this phase.")
    # Placeholder: Will need fetch_videos_for_actress_from_db(actress_slug)
    # pass
    conn = get_db_connection()
    if not conn:
        logging.error("Cannot generate actress pages: DB connection failed.")
        return

    all_actresses_info = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM actresses ORDER BY name") 
        all_actresses_info = cursor.fetchall()
        cursor.close()
    except mysql.connector.Error as err:
        logging.error(f"Error fetching actress list for pages: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()

    if not all_actresses_info:
        logging.info("No actresses found in DB to generate pages for.")
        return
    
    logging.info(f"Starting generation of {len(all_actresses_info)} actress pages...")
    
    # 僅生成前5個女優頁面作為測試
    test_limit = 5
    if test_limit:
        logging.info(f"TEST MODE: Only generating {test_limit} actress pages for testing.")
        all_actresses_info = all_actresses_info[:test_limit]

    for actress_info_row in all_actresses_info:
        try:
            actress_id = actress_info_row['id']
            actress_name_for_seo = actress_info_row['name'] # Original name for SEO title
            
            actress_page_data = fetch_actress_details_and_videos(actress_id) 

            if not actress_page_data:
                logging.warning(f"Could not fetch details for actress ID: {actress_id}. Skipping page generation.")
                continue

            for lang in ["cn", "en"]:
                output_rel_path = actress_page_data.get(f'page_path_{lang}')
                if not output_rel_path:
                    logging.error(f"Actress page path not found for actress ID {actress_id}, lang {lang}")
                    continue
                
                # Prepare context for the template 'actress_static.html'
                # The 'actress' key in context will hold actress_page_data
                # The 'videos_by_actress' key will hold actress_page_data['videos_by_actress']
                
                actress_for_template = {
                    "id": actress_page_data["id"],
                    "name_cn": actress_page_data["name_cn"],
                    "name_en": actress_page_data["name_en"],
                    "bio_cn": actress_page_data.get("bio_cn", ""),
                    "bio_en": actress_page_data.get("bio_en", ""),
                    "profile_image_url": actress_page_data.get("profile_image_url", ""), # Will use placeholder via static_paths if empty
                    "popular_tags_display": actress_page_data.get("popular_tags_display", [])
                }

                context = {
                    "lang": lang,
                    "actress": actress_for_template, 
                    "videos_by_actress": actress_page_data.get("videos_by_actress", []),
                    "seo": {
                        "title_cn": f"{actress_name_for_seo} 作品集 | MOMO Fanhao Diary",
                        "meta_description_cn": f"查看女優 {actress_name_for_seo} 的所有影片作品和相關心得。",
                        "title_en": f"{actress_name_for_seo} Profile & Videos | MOMO Fanhao Diary",
                        "meta_description_en": f"Explore all videos and works by actress {actress_name_for_seo}."
                    },
                    # Navigation URLs relative to actresses/ AID_lang.html
                    "nav_home_url": f"../index_{lang}.html", 
                    "nav_all_genres_url": f"../genres_overview_{lang}.html", 
                    "nav_all_actresses_url": f"../actresses_overview_{lang}.html", 
                    "nav_disclaimer_url": f"../disclaimer_{lang}.html"
                }
                
                # OG image for actress page (handled by write_html's static_paths using path_placeholder_og_actress)

                write_html(output_rel_path, "actress_static.html", context)
        except Exception as e:
            logging.error(f"Error generating page for actress {actress_info_row.get('name', actress_id)}: {e}")
            import traceback
            traceback.print_exc()
            continue

def generate_overview_pages():
    # logging.info("Skipping overview pages generation in this phase.")
    # Placeholder: Will need fetch_all_categories_from_db() and fetch_all_actresses_from_db()
    # pass

    all_genres = fetch_all_items_for_overview(item_type="genres")
    all_actresses = fetch_all_items_for_overview(item_type="actresses")

    # Generate Genres Overview Page
    if not all_genres:
        logging.warning("No genres found to generate genres_overview page.")
    else:
        logging.info(f"Starting generation of genres overview page with {len(all_genres)} genres...")
        for lang in ["cn", "en"]:
            output_rel_path = Path(f"genres_overview_{lang}.html")
            
            # Prepare items for template
            genres_for_template = []
            for item_data in all_genres:
                g = item_data.copy()
                page_path_obj = g.get(f"page_path_{lang}")
                g["url"] = page_path_obj.as_posix() if isinstance(page_path_obj, Path) else "#"
                g["name_display"] = g.get(f"name_{lang}", "N/A")
                genres_for_template.append(g)
            
            context = {
                "lang": lang,
                "overview_title_cn": "所有分類",
                "overview_title_en": "All Genres",
                "items": genres_for_template, # `overview_static.html` should iterate over `items`
                "item_type": "genres", # For template to know if it's genres or actresses, if needed
                "seo": {
                    "title_cn": "所有影片分類 | MOMO Fanhao Diary",
                    "meta_description_cn": "瀏覽 MOMO Fanhao Diary 中的所有影片分類列表。",
                    "title_en": "All Video Genres | MOMO Fanhao Diary",
                    "meta_description_en": "Browse the list of all video genres in MOMO Fanhao Diary.",
                },
                # Navigation URLs relative to root
                "nav_home_url": f"index_{lang}.html", 
                "nav_all_genres_url": f"genres_overview_{lang}.html", 
                "nav_all_actresses_url": f"actresses_overview_{lang}.html", 
                "nav_disclaimer_url": f"disclaimer_{lang}.html"
            }
            write_html(output_rel_path, "overview_static.html", context)

    # Generate Actresses Overview Page
    if not all_actresses:
        logging.warning("No actresses found to generate actresses_overview page.")
    else:
        logging.info(f"Starting generation of actresses overview page with {len(all_actresses)} actresses...")
        for lang in ["cn", "en"]:
            output_rel_path = Path(f"actresses_overview_{lang}.html")

            actresses_for_template = []
            for item_data in all_actresses:
                a = item_data.copy()
                page_path_obj = a.get(f"page_path_{lang}")
                a["url"] = page_path_obj.as_posix() if isinstance(page_path_obj, Path) else "#"
                a["name_display"] = a.get(f"name_{lang}", "N/A")
                actresses_for_template.append(a)

            context = {
                "lang": lang,
                "overview_title_cn": "所有女優",
                "overview_title_en": "All Actresses",
                "items": actresses_for_template,
                "item_type": "actresses",
                "seo": {
                    "title_cn": "所有女優列表 | MOMO Fanhao Diary",
                    "meta_description_cn": "瀏覽 MOMO Fanhao Diary 中的所有合作女優列表。",
                    "title_en": "All Actresses List | MOMO Fanhao Diary",
                    "meta_description_en": "Browse the list of all actresses featured in MOMO Fanhao Diary.",
                },
                "nav_home_url": f"index_{lang}.html", 
                "nav_all_genres_url": f"genres_overview_{lang}.html", 
                "nav_all_actresses_url": f"actresses_overview_{lang}.html", 
                "nav_disclaimer_url": f"disclaimer_{lang}.html"
            }
            write_html(output_rel_path, "overview_static.html", context)

def generate_disclaimer_pages():
    # This page is mostly static, might not need DB data or minimal
    for lang in ["cn", "en"]:
        page_path = Path(f"disclaimer_{lang}.html")
        context = {
            "lang": lang,
            "page_title": "關於本站與免責聲明" if lang == "cn" else "About & Disclaimer",
            "seo": { "title_cn": "免責聲明 | MOMO Fanhao Diary", "title_en": "Disclaimer | MOMO Fanhao Diary" }
        }
        write_html(page_path, "disclaimer_static.html", context)

def generate_404_pages():
    """生成自定义404页面"""
    logging.info("Generating 404 pages...")
    
    # 中文版404页面
    context_cn = {
        'lang': 'cn',
        'current_year': datetime.now(timezone.utc).year,
        'alternate_lang_url': '/en/404.html',
        'path_css': '/static/style.css',
        'path_favicon': '/static/favicon.png',
        'path_ad_js': '/static/ad.js',
        'path_search_js': '/static/search.js',
        'path_path_resolver_js': '/static/path-resolver.js',
        'current_page_url': '/404.html'
    }
    
    # 英文版404页面
    context_en = {
        'lang': 'en',
        'current_year': datetime.now(timezone.utc).year,
        'alternate_lang_url': '/404.html',
        'path_css': '/static/style.css',
        'path_favicon': '/static/favicon.png',
        'path_ad_js': '/static/ad.js',
        'path_search_js': '/static/search.js',
        'path_path_resolver_js': '/static/path-resolver.js',
        'current_page_url': '/en/404.html'
    }
    
    # 写入中文和英文版404页面
    write_html(Path("404.html"), "404_static.html", context_cn)
    write_html(Path("en/404.html"), "404_static.html", context_en)

def generate_lang_redirect():
    """生成语言自动选择功能的脚本"""
    logging.info("Generating language redirect script...")
    
    redirect_js = """// Language auto-redirect script
document.addEventListener('DOMContentLoaded', function() {
    // Check if this is the first visit (no language preference stored)
    if(!localStorage.getItem('lang_preference')) {
        // Get browser language
        const userLang = navigator.language || navigator.userLanguage;
        
        // If current path is root
        if(window.location.pathname === '/' || window.location.pathname === '/index.html') {
            // If browser language starts with zh, redirect to Chinese
            if(userLang.startsWith('zh')) {
                localStorage.setItem('lang_preference', 'cn');
                window.location.href = '/index_cn.html';
            } else {
                // Otherwise redirect to English
                localStorage.setItem('lang_preference', 'en');
                window.location.href = '/en/index_en.html';
            }
        }
    }
});
"""
    
    # 确保静态目录存在
    static_js_dir = OUTPUT_DIR / "static" / "js"
    static_js_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入脚本
    with open(static_js_dir / "lang-redirect.js", "w", encoding="utf-8") as f:
        f.write(redirect_js)
    
    # 写入主页的自动跳转页面
    index_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MOMO Fanhao Diary</title>
    <link rel="icon" href="/static/favicon.png" type="image/png">
    <script src="/static/js/lang-redirect.js"></script>
    <style>
        body {
            font-family: 'Noto Sans SC', 'Roboto', 'Segoe UI', sans-serif;
            background-color: #FFF8F0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: #333;
        }
        .loading {
            text-align: center;
        }
        .loading h1 {
            color: #FF69B4;
            font-size: 2em;
            margin-bottom: 10px;
        }
        .spinner {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #FF69B4;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 2s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="loading">
        <h1>MOMO Fanhao Diary</h1>
        <div class="spinner"></div>
        <p>Loading your preferred language...</p>
        <script>
            // Redirect fallback
            setTimeout(function() {
                window.location.href = '/index_cn.html';
            }, 1500);
        </script>
    </div>
</body>
</html>"""
    
    # 写入根目录的index.html
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

def copy_static_files():
    """复制静态文件到输出目录"""
    logging.info("Copying static files...")
    
    # 创建静态文件目录
    static_dir = OUTPUT_DIR / "static"
    static_dir.mkdir(exist_ok=True)
    
    # 复制所有静态文件
    shutil.copytree(PUBLIC_STATIC_DIR, static_dir, dirs_exist_ok=True)
    
    # 确保favicon.ico存在（浏览器常常会尝试请求这个文件）
    favicon_ico = static_dir / "favicon.ico"
    favicon_png = static_dir / "favicon.png"
    favicon_svg = static_dir / "favicon.svg"
    
    # 如果有SVG版本的favicon，优先使用SVG
    if favicon_svg.exists():
        logging.info("Found favicon.svg. Using as primary favicon.")
        # 确保生成了对应的PNG和ICO版本
        shutil.copy(favicon_svg, favicon_png)
    
    # 为防止404错误，确保favicon.ico存在
    if not favicon_ico.exists() and favicon_png.exists():
        shutil.copy(favicon_png, favicon_ico)
    
    logging.info("Static files copied successfully.")

# --- 主執行流程 ---
def main():
    logging.info("開始生成靜態網站 (使用資料庫數據)...")
    
    if not all([DB_HOST, DB_USER, DB_NAME]): # DB_PASSWORD can be empty for local dev
        logging.error("Database configuration is missing or incomplete in .env file. ")
        logging.error("Please ensure DB_HOST, DB_USER, DB_NAME are set.")
        logging.error("DB_PASSWORD can be empty if your local MySQL user has no password.")
        return

    # 1. 清理並創建 output 目錄結構
    if OUTPUT_DIR.exists():
        try:
            shutil.rmtree(OUTPUT_DIR)
            logging.info(f"已清除舊的 output 目錄: {OUTPUT_DIR}")
        except OSError as e:
            logging.error(f"Error removing {OUTPUT_DIR}: {e.strerror} - Please check file permissions or if files are in use.")
            return # Stop if cannot clear output dir
            
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "videos").mkdir(exist_ok=True)
    (OUTPUT_DIR / "genres").mkdir(exist_ok=True) # Add genres directory
    (OUTPUT_DIR / "actresses").mkdir(exist_ok=True)
    static_target_dir = OUTPUT_DIR / "static"

    # 2. 複製 public/static 下的靜態檔案到 output/static
    if PUBLIC_STATIC_DIR.exists() and PUBLIC_STATIC_DIR.is_dir():
        shutil.copytree(PUBLIC_STATIC_DIR, static_target_dir, dirs_exist_ok=True)
        logging.info(f"靜態檔案已從 {PUBLIC_STATIC_DIR} 複製到 {static_target_dir}")
    else:
        logging.warning(f"{PUBLIC_STATIC_DIR} 不存在或不是目錄。將不會複製靜態檔案。")
        static_target_dir.mkdir(exist_ok=True) 

    # 3. 生成各類頁面 (Focus on index first)
    generate_index_pages()
    generate_detail_pages()
    generate_genre_pages()
    generate_actress_pages()
    generate_overview_pages()
    generate_disclaimer_pages()
    generate_404_pages()
    generate_lang_redirect()
    copy_static_files()

    logging.info("網站生成完畢！所有檔案位於 output/ 目錄下。")

if __name__ == "__main__":
    main() 