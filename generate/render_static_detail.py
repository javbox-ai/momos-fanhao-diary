import os
import logging
from dotenv import load_dotenv
import mysql.connector
from openai import OpenAI # For DeepSeek
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, timedelta, timezone
import re

# --- Configuration & Setup ---
# Load environment variables from .env file
expected_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
print(f"Attempting to load .env file from: {expected_env_path}")
load_dotenv(dotenv_path=expected_env_path)

# Logging Configuration
LOG_FILE = os.path.join(os.path.dirname(__file__), 'render_static_detail.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Project Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
OUTPUT_DIR_BASE = os.path.join(PROJECT_ROOT, 'output', 'videos')
STATIC_BASE_PATH = "/static" # As required

# Environment Variables with Fallbacks
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_DATABASE = os.getenv('DB_DATABASE', 'missav_db')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL') # e.g., "https://api.deepseek.com/v1"
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000').rstrip('/')

# OpenAI Client for DeepSeek
client = None
if DEEPSEEK_API_KEY and DEEPSEEK_API_URL:
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)
        logging.info("OpenAI client initialized for DeepSeek.")
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client for DeepSeek: {e}")
else:
    logging.warning("DeepSeek API key or URL not found in .env. AI features will be disabled or use fallbacks.")

# --- NEW/MODIFIED Helper Functions ---
def generate_content_with_deepseek(prompt_text, video_code_for_logging="N/A_USER_LOOP", content_type="content_USER_LOOP"):
    global client
    if not client:
        logging.warning(f"AI client not available. Returning fallback for {content_type} for {video_code_for_logging}.")
        return "AI generation failed (client not initialized)" # Consistent with user's "failed in" check
    try:
        # Log the actual prompt being sent for debugging
        logging.info(f"Requesting AI completion for {content_type} for {video_code_for_logging}. Prompt: '{prompt_text}'")
        response = client.chat.completions.create(
            model="deepseek-chat", # As per user's last request
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=600, # Increased slightly for potentially longer reviews
            temperature=0.7,
        )
        ai_text = response.choices[0].message.content.strip()
        logging.info(f"Successfully received AI completion for {content_type} for {video_code_for_logging}.")
        # User's loop has its own print statements for AI content
        return ai_text
    except Exception as e:
        logging.error(f"Error getting AI completion for {content_type} for {video_code_for_logging}: {e}")
        return f"AI generation failed ({e})" # Consistent with user's "failed in" check

def translate_list_to_english(items_list, item_type="item"):
    # Placeholder: Actual translation logic needed
    # This could involve calling generate_content_with_deepseek for each item
    logging.warning(f"Placeholder function 'translate_list_to_english' called for {item_type}. Needs proper implementation.")
    translated_list = []
    for item in items_list:
        # Example of how you might call the AI for translation:
        # prompt = f"Translate the following {item_type} to English: '{item}'. Output ONLY the translated text."
        # translated_item = generate_content_with_deepseek(prompt, content_type=f"Translate {item_type}")
        # if "failed" in translated_item:
        #     translated_list.append(f"{item}_EN_placeholder (translation failed)")
        # else:
        #     translated_list.append(translated_item)
        translated_list.append(f"{item}_EN_placeholder") # Current placeholder behavior
    return translated_list

def get_static_paths(base_url_param):
    logging.info(f"Function 'get_static_paths' called. base_url_param is: {base_url_param}")
    # Ensure base_url_param does not end with a slash for clean joining
    clean_base_url = base_url_param.rstrip('/')
    return {
        "path_css": f"{clean_base_url}/static/style.css",
        "path_favicon": f"{clean_base_url}/static/favicon.png",
        "path_logo": f"{clean_base_url}/static/LOGO.png",
        "path_ad_js": f"{clean_base_url}/static/ad.js",
        "path_search_js": f"{clean_base_url}/static/search.js",
        "path_path_resolver_js": f"{clean_base_url}/static/path-resolver.js",
        "path_static_images": f"{clean_base_url}/static/images",
        "path_placeholder_thumb": f"{clean_base_url}/static/images/placeholder_thumb.png" # Added for index/category pages
    }

# --- ORIGINAL Helper Functions (keeping as they might be useful or partially used) ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE
        )
        logging.info("Successfully connected to MySQL database.")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to MySQL: {err}")
        return None

def fetch_latest_videos(conn, limit=10):
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT
                v.id,
                v.code,
                v.title,
                v.cover_url,
                v.description,
                v.release_date,
                GROUP_CONCAT(DISTINCT a.name) AS actresses,
                GROUP_CONCAT(DISTINCT g.name) AS genres,
                GROUP_CONCAT(DISTINCT s.name) AS series,
                GROUP_CONCAT(DISTINCT l.name) AS labels
            FROM videos v
            LEFT JOIN video_actress va ON v.id = va.video_id
            LEFT JOIN actresses a ON va.actress_id = a.id
            LEFT JOIN video_genre vg ON v.id = vg.video_id
            LEFT JOIN genres g ON vg.genre_id = g.id
            LEFT JOIN video_series vs ON v.id = vs.video_id
            LEFT JOIN series s ON vs.series_id = s.id
            LEFT JOIN video_label vl ON v.id = vl.video_id
            LEFT JOIN labels l ON vl.label_id = l.id
            GROUP BY v.id
            ORDER BY v.id DESC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        videos = cursor.fetchall()
        logging.info(f"Fetched {len(videos)} videos from the database.")
        return videos
    except mysql.connector.Error as err:
        logging.error(f"Error fetching videos from MySQL: {err.msg if err.msg else err}")
        logging.error(f"Failed SQL Query: {cursor.statement if cursor else 'Cursor not available'}")
        return []
    finally:
        if cursor:
            cursor.close()

def generate_mock_videos(count=3):
    logging.info(f"Using {count} mock videos for testing.")
    mock_video_list = []
    for i in range(1, count + 1):
        fanhao = f"MOCK-{str(i).zfill(3)}"
        mock_video_list.append({
            'id': i, # Numeric ID for mock
            'code': fanhao,
            'title': f'Mock 中文标题 {i}',
            'cover_url': f'{STATIC_BASE_PATH}/images/placeholder_cover_clear.png', # Example, may need adjustment
            'release_date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
            'actresses': f'模擬女優{i}A,模擬女優{i}B', # Comma-separated string
            'genres': f'模擬分類{i}X,模擬分類{i}Y',     # Comma-separated string
            'series': f'模擬系列{i}',                   # Comma-separated string
            'labels': f'模擬標籤{i}S,模擬標籤{i}T',     # Comma-separated string
            'description': f'這是 {fanhao} 的模擬中文簡介。包含了一些基本信息和劇情概述。',
        })
    return mock_video_list

def safe_get(data_dict, key, default="N/A"): # Kept from original, might be useful
    val = data_dict.get(key)
    return val if val not in [None, ''] else default

def generate_placeholder_image_url(image_type="cover"): # Kept from original
    clean_base_url = BASE_URL.rstrip('/')
    if image_type == "og":
        return f"{clean_base_url}/static/images/placeholder_og_video.png"
    elif image_type == "blurred":
        return f"{clean_base_url}/static/images/placeholder_cover_blurred.png"
    return f"{clean_base_url}/static/images/placeholder_cover_clear.png"

# --- Jinja2 Environment ---
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)
# Ensure the date filter is compatible if used by the template.
# The user's loop does not seem to use it in render_data, but the template might.
# Original: jinja_env.filters['date'] = lambda value, fmt_str: datetime.utcnow().strftime(fmt_str)
# Using now(datetime.UTC) for future compatibility
jinja_env.filters['date'] = lambda value, fmt_str: datetime.now(timezone.utc).strftime(fmt_str)


# --- Main Generation Logic ---
def main():
    logging.info("Starting static detail page generation script (with new user loop structure).")
    
    FULL_ABSOLUTE_URL_PREFIX = BASE_URL # Defined from global BASE_URL
    current_year = datetime.now().year

    db_conn = get_db_connection()
    raw_videos_from_db = fetch_latest_videos(db_conn, limit=10)
    
    if db_conn and db_conn.is_connected():
        db_conn.close()
        logging.info("MySQL connection closed.")

    source_videos = raw_videos_from_db if raw_videos_from_db else generate_mock_videos(3)
    if not source_videos:
        logging.error("No video data available (neither DB nor mock). Exiting.")
        return

    if not os.path.exists(OUTPUT_DIR_BASE):
        os.makedirs(OUTPUT_DIR_BASE)
        logging.info(f"Created output directory: {OUTPUT_DIR_BASE}")

    # Prepare video_data_list for the user's loop
    video_data_list = []
    for idx, raw_item in enumerate(source_videos):
        processed_item = {}
        processed_item['numeric_id'] = raw_item.get('id') # For print: "Processing video: {video_data['id']}"
                                                       # User's loop seems to expect video_data['id'] to be the fanhao for video_code
                                                       # Let's clarify: 'id' for display, 'code' for fanhao.
        
        # User loop: video_code = video_data.get('id', 'N/A')
        # This implies 'id' key in video_data should be the fanhao.
        # So, raw_item.get('code') should be mapped to 'id' in video_data for the loop.
        # And the numeric db_id should be stored separately if needed for printing.
        
        fanhao = raw_item.get('code', f"UNKNOWN_FANHAO_{idx+1}")
        processed_item['id'] = fanhao # For user's loop: video_data.get('id') -> video_code
        processed_item['db_id_for_print'] = raw_item.get('id', 'N/A_DB_ID') # For printing numeric ID
        processed_item['code'] = fanhao # Explicit fanhao field

        processed_item['title'] = raw_item.get('title', '未知標題')
        
        actresses_str = raw_item.get('actresses', "")
        actress_list = [a.strip() for a in actresses_str.split(',') if a.strip()] if actresses_str else []
        processed_item['actress'] = actress_list[0] if actress_list else "未知演員"
        processed_item['all_actresses_list_cn'] = actress_list # Keep full list for template if needed

        genres_str = raw_item.get('genres', "")
        processed_item['genres'] = [g.strip() for g in genres_str.split(',') if g.strip()] if genres_str else []
        
        labels_str = raw_item.get('labels', "")
        processed_item['labels'] = [l.strip() for l in labels_str.split(',') if l.strip()] if labels_str else []

        series_str = raw_item.get('series', "") # Keep series if template uses it
        processed_item['series_list_cn'] = [s.strip() for s in series_str.split(',') if s.strip()] if series_str else []


        processed_item['base_info_for_ai'] = raw_item.get('description', '')
        processed_item['original_description'] = raw_item.get('description', '') # For plot summary in template

        processed_item['release_date'] = raw_item.get('release_date', "N/A")

        # Cover URL processing (from original script, now with BASE_URL)
        db_cover_url = raw_item.get('cover_url')
        processed_cover_url_path = ""
        clean_base_url_for_images = BASE_URL.rstrip('/') # ensure BASE_URL is accessible here
        if db_cover_url:
            if db_cover_url.startswith('http://') or db_cover_url.startswith('https://'):
                processed_cover_url_path = db_cover_url
            else:
                # Ensure no double slashes if db_cover_url starts with /
                processed_cover_url_path = f"{clean_base_url_for_images}/static/images/{db_cover_url.lstrip('/')}"
        
        processed_item['og_image_url'] = processed_cover_url_path if processed_cover_url_path else generate_placeholder_image_url("og")
        processed_item['cover_image_url_clear'] = processed_cover_url_path if processed_cover_url_path else generate_placeholder_image_url("clear")
        processed_item['cover_image_url_blurred'] = generate_placeholder_image_url("blurred") # Uses BASE_URL from its own definition now

        video_data_list.append(processed_item)

    # --- User's Loop Starts ---
    processed_count = 0
    for video_data in video_data_list: # video_data is an item from the prepared list
        try:
            # video_data['id'] is the fanhao/code here, db_id_for_print is the numeric one
            print(f"\n--- Processing video (DB_ID: {video_data.get('db_id_for_print', 'N/A')}, CODE: {video_data.get('id')}) ---")
            print("Generating AI content...")
            
            # These are now directly from the pre-processed video_data
            video_title = video_data.get('title', '未知標題')
            video_code = video_data.get('id', 'N/A') # This is the fanhao
            actress_name = video_data.get('actress', '未知演員')
            genres_list = video_data.get('genres', []) # This is now a list of strings
            base_description = video_data.get('base_info_for_ai', '') # This is the original description
            
            keywords = ', '.join(genres_list[:3]) if genres_list else '無'
            # For keywords_en, translate genres_list first if needed, or use English genres if available
            # Assuming translate_list_to_english handles this.
            # The user's loop calls translate_list_to_english for video_data['genres_en'] later.
            # So keywords_en should use that.
            
            # Ensure actress_name_en is derived correctly
            primary_actress_en_name_placeholder = f"{actress_name} EN" if actress_name != '未知演員' else 'Unknown Actress'
            # If proper translation is available later, this might be updated. For now, using placeholder.
            actress_name_en = primary_actress_en_name_placeholder

            print(f"開始翻譯影片 {video_code} 的 Genres 和 Tags (Labels)...")
            # These will be added to the video_data dictionary itself for use in EN prompts/template
            video_data['genres_en'] = translate_list_to_english(genres_list, "genre")
            video_data['tags_en'] = translate_list_to_english(video_data.get('labels', []), "tag") # labels are tags

            keywords_en = ', '.join(video_data['genres_en'][:3]) if video_data['genres_en'] else 'None'


            # --- AI 內容生成 ---
            # 中文 Prompt
            rewrite_title_prompt_zh = f"請將以下影片標題 '{video_title}' 用稍微不同的方式表達，保持意思和長度相似，作為網頁標題使用。"
            print("Rewriting title with AI (Chinese)...")
            # Use video_code (fanhao) for logging context in generate_content_with_deepseek
            raw_ai_rewritten_title_zh = generate_content_with_deepseek(rewrite_title_prompt_zh, video_code, "Chinese Title Rewrite")
            ai_rewritten_title_zh = ""
            if "failed" in raw_ai_rewritten_title_zh.lower() or not raw_ai_rewritten_title_zh: # case-insensitive check
                print("AI title rewrite failed (Chinese), using original title.")
                ai_rewritten_title_zh = video_title
            else:
                ai_rewritten_title_zh = raw_ai_rewritten_title_zh.split('\n')[0].strip()
                if not ai_rewritten_title_zh or '(' in ai_rewritten_title_zh: # Original check
                    print("AI title rewrite resulted in empty/invalid string after processing, using original title.")
                    ai_rewritten_title_zh = video_title
            
            # 僅直接翻譯英文標題，不做 SEO 或多餘內容
            translate_title_prompt_en = f"Translate the following Japanese adult video title strictly into English. Output ONLY the translated title. Do not include the original title, any introductory text, or quotation marks. Just the English translation.\nTitle: '{video_title}'"
            print("Translating title with AI (English)...")
            raw_ai_translated_title_en = generate_content_with_deepseek(translate_title_prompt_en, video_code, "English Title Translation")
            ai_translated_title_en = ""
            if "failed" in raw_ai_translated_title_en.lower() or not raw_ai_translated_title_en:
                print("AI title translation failed (English), using original title.")
                ai_translated_title_en = video_title # Fallback to original (possibly Chinese) title
            else:
                ai_translated_title_en = raw_ai_translated_title_en.split('\n')[0].strip()
                if not ai_translated_title_en or '(' in ai_translated_title_en: # Original check
                    print("AI title translation resulted in empty/invalid string after processing, using original title.")
                    ai_translated_title_en = video_title # Fallback

            # 生成 SEO 摘要
            seo_prompt_zh = f"請為以下影片撰寫一段短的 SEO meta description (約 50-70 字)，重點強調影片特色和吸引力，包含番號 '{video_code}' 和女優 '{actress_name}'。影片標題：'{video_title}'，類型：{keywords}。請直接輸出描述文字，不要包含字數統計或其他額外說明。"
            print("Generating SEO summary (Chinese)...")
            seo_summary_zh = generate_content_with_deepseek(seo_prompt_zh, video_code, "Chinese SEO Summary")
            if "failed" in seo_summary_zh.lower(): seo_summary_zh = f"探索 {video_code} ({actress_name}) 的精彩影片「{ai_rewritten_title_zh}」。"
            else: seo_summary_zh = re.sub(r'\s*\(\d+\s*chars\)$', '', seo_summary_zh).strip()
            
            seo_prompt_en = f"Write a short SEO meta description (around 50-70 characters) for the following video, highlighting its features and appeal. Include the code '{video_code}' and actress '{actress_name_en}'. Video Title: '{ai_translated_title_en}', Genres: {keywords_en}. Output only the description text." # Use translated title for EN SEO
            print("Generating SEO summary (English)...")
            seo_summary_en = generate_content_with_deepseek(seo_prompt_en, video_code, "English SEO Summary")
            if "failed" in seo_summary_en.lower(): seo_summary_en = f"Discover '{ai_translated_title_en}' starring {actress_name_en} ({video_code})."
            else: seo_summary_en = re.sub(r'\s*\(\d+\s*chars\)$', '', seo_summary_en).strip()

            # 生成中文心得
            review_prompt_zh = f"""你是一位 20 出頭的女大學生，平常會偷偷看片，並寫下觀影筆記當作深夜小日記。
請幫我撰寫一篇 番號為「{video_code}」的心得筆記，風格要口語、生動、微色色，適合投稿到部落格或心得網站。
請模仿真實人類的語氣，並依以下段落撰寫：
觀影動機開場：用女大生視角，簡單講為什麼會點進這部（像是在考前偷滑手機、朋友推薦之類）
觀賞過程描寫：選擇最印象深刻的一幕，用描述角色、對白、畫面、高潮等細節方式，語氣可以興奮、害羞或瘋狂。
結尾總結 & 私密感想：可愛地碎念或反思（例如：這男優太壞了、我以後可能會愛上這類型等等）
注意事項：
使用親暱、口語、非正式語氣（像寫給閨蜜看的那種）
請控制在 400～600字左右，以利 SEO 收錄與用戶閱讀
可適度加入貼標籤語（如：#制服控 #主觀視角 #潮吹 #想再看一遍）
避免過度重複 AI 用詞，務必有段落、句式變化
影片標題：'{ai_rewritten_title_zh}'，女優：'{actress_name}'，類型：{keywords}。原始簡介：'{base_description}'"""
            print("Generating review (Chinese - College Girl Style)...")
            ai_content_zh = generate_content_with_deepseek(review_prompt_zh, video_code, "Chinese Review")
            if "failed" in ai_content_zh.lower() or not ai_content_zh:
                print("AI review generation failed (Chinese), using placeholder.")
                ai_content_zh = f"<p>AI 心得生成失敗 ({video_code})</p>"

            # 生成英文心得
            review_prompt_en = f"""You are a slightly horny, cheeky college girl who writes casual movie notes as late-night diary entries.
Please help me write a review-style note for the JAV movie with code {video_code}.
The tone should be playful, immersive, flirty, and ultra-conversational — like a tweet-thread meets Tumblr fangirl blog.
Structure your writing into these three short but juicy sections:
Why I clicked it – casual intro (like: "I was bored, scrolling, and BAM—this thumbnail hit me" or "a friend dared me to watch this")
What made me lose my mind – describe 1–2 moments from the scene in emotional/visual detail (moans, positions, how it felt to watch)
Afterthoughts – your emotional state after finishing (ex: "I need a shower," "lowkey bookmarked it," "might watch it again tbh")
Stylistic notes:
Use TikTok-style expressions, emoji, asides (italic comments), and lots of ellipses / line breaks
Aim for 400–600 words, naturally spaced with paragraphs
Avoid AI-sounding vocabulary (make it sound real, slightly chaotic, like horny texting)
You can include hashtags like #Creampie #POV #LateNightRewatch etc.
Video Title: '{ai_translated_title_en}', Actress: '{actress_name_en}', Genres: {keywords_en}. Original Description: '{base_description}'"""
            print("Generating review (English - Horny College Girl Style)...")
            ai_content_en = generate_content_with_deepseek(review_prompt_en, video_code, "English Review")
            if "failed" in ai_content_en.lower() or not ai_content_en:
                print("AI review generation failed (English), using placeholder.")
                ai_content_en = f"<p>AI review generation failed ({video_code})</p>"
            
            # --- Prepare data for template rendering ---
            # The user's render_data needs to be adapted to fit detail_static.html
            # The template expects: video.fanhao, video.actress_cn, video.ai_title_cn, video.ai_review_cn, etc.
            # And seo.meta_description_cn

            # Update video_data with generated AI content for the template
            video_data['fanhao'] = video_code # Redundant as video_data['id'] is already fanhao, but explicit for template
            video_data['actress_cn'] = actress_name
            video_data['actress_en'] = actress_name_en # Use the (potentially placeholder) English actress name
            
            video_data['ai_title_cn'] = ai_rewritten_title_zh
            video_data['ai_title_en'] = ai_translated_title_en
            video_data['ai_review_cn'] = ai_content_zh
            video_data['ai_review_en'] = ai_content_en
            
            # For plot summary, use original description
            video_data['plot_summary_cn'] = base_description 
            video_data['plot_summary_en'] = base_description # Assuming simple pass-through for EN summary

            # Dynamic URLs for genres and actress (adapted from original script)
            # video_data already has 'genres' (list of CN strings) and 'all_actresses_list_cn'
            video_data['genre_links_for_template_cn'] = []
            for g_cn in video_data['genres']:
                video_data['genre_links_for_template_cn'].append({
                    'name_cn': g_cn, 'name_en': f"{g_cn}_EN", # Placeholder for EN name if not properly translated
                    'url': f"/category/{g_cn.lower().replace(' ','-') if g_cn != 'N/A' else 'na'}_cn.html"
                })
            video_data['genre_links_for_template_en'] = []
            for g_en in video_data['genres_en']: # Assumes genres_en is populated
                g_cn_source = video_data['genres'][video_data['genres_en'].index(g_en)] if g_en.endswith("_EN_placeholder") and video_data['genres_en'].index(g_en) < len(video_data['genres']) else g_en # Try to get original for URL
                video_data['genre_links_for_template_en'].append({
                    'name_cn': g_cn_source.replace("_EN_placeholder",""), 'name_en': g_en,
                    'url': f"/category/{g_cn_source.lower().replace(' ','-').replace('_en_placeholder','_en') if g_cn_source != 'N/A' else 'na'}_en.html"
                })

            video_data['actress_url_cn'] = f"/actress/{actress_name.lower().replace(' ','-') if actress_name != '未知演員' else 'na'}_cn.html"
            video_data['actress_url_en'] = f"/actress/{actress_name_en.lower().replace(' ','-') if actress_name_en != 'Unknown Actress' else 'na'}_en.html"
            
            # Tags (from labels and series)
            series_tags_cn = [{'name_cn': t.strip(), 'name_en': f"{t.strip()}_EN"} for t in video_data.get('series_list_cn', [])]
            labels_tags_cn = [{'name_cn': t.strip(), 'name_en': f"{t.strip()}_EN"} for t in video_data.get('labels', [])] # labels are already list of strings
            video_data['tags_for_template'] = series_tags_cn + labels_tags_cn


            seo_context_for_template_zh = {'meta_description_cn': seo_summary_zh}
            seo_context_for_template_en = {'meta_description_en': seo_summary_en}
            
            static_paths_dict = get_static_paths(BASE_URL)

            # Render Chinese page
            page_context_zh = {
                'lang': 'cn',
                'video': video_data, # This now contains most necessary fields for {{ video. ... }}
                'seo': seo_context_for_template_zh,
                'current_page_url': f"{FULL_ABSOLUTE_URL_PREFIX}/videos/{video_code}_zh.html",
                'alternate_lang_url': f"/videos/{video_code}_en.html",
                'current_year': current_year,
                 **static_paths_dict # Spread static paths directly into context
            }
            # Adapt genres for Chinese page context (use cn links)
            page_context_zh['video']['genres'] = video_data['genre_links_for_template_cn']
            page_context_zh['video']['actress_url'] = video_data['actress_url_cn']


            # Render English page
            page_context_en = {
                'lang': 'en',
                'video': video_data.copy(), # Use a copy to modify 'genres' and 'actress_url' specifically for EN
                'seo': seo_context_for_template_en,
                'current_page_url': f"{FULL_ABSOLUTE_URL_PREFIX}/videos/{video_code}_en.html",
                'alternate_lang_url': f"/videos/{video_code}_zh.html",
                'current_year': current_year,
                **static_paths_dict
            }
            # Adapt video data for English page context
            page_context_en['video']['genres'] = video_data['genre_links_for_template_en'] # Use en links
            page_context_en['video']['actress_url'] = video_data['actress_url_en']
            # Ensure EN fields are used for main display if different from CN in video_data
            page_context_en['video']['actress_name_display'] = actress_name_en # For {{ video.actress_name_display }}
            page_context_en['video']['title_display'] = ai_translated_title_en # For {{ video.title_display }}
            page_context_en['video']['review_display'] = ai_content_en # For {{ video.review_display }}


            # --- Template Rendering (adapted from original) ---
            for lang_code, page_context_to_render, template_lang_setting in [('zh', page_context_zh, 'cn'), ('en', page_context_en, 'en')]:
                try:
                    # This overrides 'lang' in page_context_to_render if it was set differently
                    page_context_to_render['lang'] = template_lang_setting 
                    
                    template = jinja_env.get_template('detail_static.html')
                    html_content = template.render(page_context_to_render)
                    output_filename = f"{video_code}_{lang_code}.html" # Use video_code (fanhao)
                    output_filepath = os.path.join(OUTPUT_DIR_BASE, output_filename)
                    with open(output_filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logging.info(f"Successfully generated: {output_filepath}")
                except Exception as e:
                    logging.error(f"Error rendering or writing file for {video_code}_{lang_code}.html: {e}", exc_info=True)
            
            processed_count += 1

        except Exception as e:
            # Use fanhao (video_code) if available in video_data, otherwise use a generic error name
            current_fanhao_for_error = video_data.get('id', f"ERROR_VIDEO_UNKNOWN_ID_{processed_count+1}")
            logging.error(f"Unhandled error processing video data for {current_fanhao_for_error}: {e}", exc_info=True)
            for lang_code_err in ['zh', 'en']:
                try:
                    err_file_path = os.path.join(OUTPUT_DIR_BASE, f"{current_fanhao_for_error}_{lang_code_err}.html")
                    with open(err_file_path, 'w', encoding='utf-8') as f_err:
                        f_err.write(f"<html><body><h1>Error generating page for {current_fanhao_for_error} ({lang_code_err})</h1><p>{e}</p></body></html>")
                    logging.info(f"Generated error placeholder page: {err_file_path}")
                except Exception as e_file:
                    logging.error(f"Could not write error placeholder page for {current_fanhao_for_error}_{lang_code_err}: {e_file}")
    # --- User's Loop Ends ---

    logging.info(f"Script finished. Processed {processed_count} videos with new loop structure.")
    if processed_count > 0:
         logging.info(f"Check {OUTPUT_DIR_BASE} for generated HTML files. Log file: {LOG_FILE}")
    else:
         logging.info(f"No videos were processed with new loop. Check logs. Log file: {LOG_FILE}")

if __name__ == '__main__':
    placeholder_images_dir = os.path.join(PROJECT_ROOT, 'public', 'static', 'images')
    if not os.path.exists(placeholder_images_dir):
        os.makedirs(placeholder_images_dir)
    
    placeholders_to_create = [
        'placeholder_cover_clear.png', 'placeholder_cover_blurred.png',
        'placeholder_og_video.png', 'LOGO.png', 'favicon.png'
    ]
    for p_img in placeholders_to_create:
        p_path = os.path.join(placeholder_images_dir, p_img)
        if not os.path.exists(p_path):
            try:
                with open(p_path, 'w', encoding='utf-8') as f: 
                    f.write(f"This is a placeholder for {p_img}")
                logging.info(f"Created placeholder image: {p_path}")
            except IOError as e:
                logging.warning(f"Could not create placeholder image {p_path}: {e}")
    main() 