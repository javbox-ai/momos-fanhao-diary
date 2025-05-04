import requests
from jinja2 import Environment, FileSystemLoader
import os
import mysql.connector # 新增
from datetime import datetime # 新增
import re # 新增，用於生成安全的文件名
import json # 新增，用於處理 JSON
import requests # 確保導入 requests
import time # 導入 time 模塊用於重試延遲

# --- 資料庫連接資訊 (從 app.py 複製並調整) ---
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'yoyo0024'),
    'database': os.getenv('DB_DATABASE', 'missav_db')
}

connection_config = {
    'user': DATABASE_CONFIG['user'],
    'password': DATABASE_CONFIG['password'],
    'host': DATABASE_CONFIG['host'],
    'database': DATABASE_CONFIG['database']
}

# --- DeepSeek API 設定 ---
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', "sk-dc0e894e0fe041a2b251b0694cba0b79")
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', "https://api.deepseek.com/v1/chat/completions")

def get_db_connection():
    try:
        conn = mysql.connector.connect(**connection_config)
        print("資料庫連接成功")
        return conn
    except Exception as e:
        print(f"資料庫連接錯誤: {e}")
        return None

def fetch_top_video_details():
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT
                v.code AS id,
                v.title,
                v.cover_url AS cover_image,
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
            LIMIT 10 # 改為獲取最新的 10 筆
        """
        cursor.execute(query)
        video_details = cursor.fetchall()
        processed_details = []
        if video_details:
            print(f"從資料庫成功獲取 {len(video_details)} 筆影片的詳細資訊")
            for video_detail in video_details:
                print(f"  處理影片 {video_detail['id']}...")
                if not video_detail['cover_image']:
                    video_detail['cover_image'] = '/static/placeholder.jpg'
                for key in ['actresses', 'genres', 'series', 'labels']:
                    if video_detail[key]:
                        video_detail[key] = video_detail[key].split(',')
                    else:
                        video_detail[key] = []
                if video_detail['release_date'] and isinstance(video_detail['release_date'], datetime):
                     video_detail['release_date'] = video_detail['release_date'].strftime('%Y-%m-%d')
                elif not video_detail['release_date']:
                     video_detail['release_date'] = 'N/A'
                video_detail['actress'] = video_detail['actresses'][0] if video_detail['actresses'] else 'Unknown Actress'
                video_detail['category'] = video_detail['genres'][0] if video_detail['genres'] else 'Unknown Category'
                video_detail['tags'] = ','.join(video_detail['genres']) if video_detail['genres'] else ''
                video_detail['duration'] = video_detail.get('duration', 'N/A')
                video_detail['base_info_for_ai'] = video_detail.get('description', '')
                processed_details.append(video_detail)
        else:
            print("在資料庫中找不到任何影片")
    except mysql.connector.Error as err:
        print(f"查詢第一筆影片詳細資訊時發生錯誤: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")
    return processed_details

def generate_content_with_deepseek(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    response = None
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if result.get('choices') and len(result['choices']) > 0:
            return result['choices'][0].get('message', {}).get('content', '').strip()
        else:
            print("Error: Unexpected API response format.")
            print(result)
            return "(AI content generation failed)"
    except requests.exceptions.RequestException as e:
        print(f"Error calling DeepSeek API: {e}")
        if response:
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
        return "(AI content generation failed due to network error)"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "(AI content generation failed due to unexpected error)"

def translate_list_to_english(items):
    if not items:
        return []
    translated_items = []
    for item in items:
        item_str = str(item).strip()
        if not item_str:
            continue
        translated_item = None
        for attempt in range(3):
            prompt = f"""Translate the following word or short phrase strictly into English. Output ONLY the translated word/phrase. Do not include the original text, any introductory text, or quotation marks. Just the English translation.\n\nPhrase: '{item_str}'"""
            api_result = generate_content_with_deepseek(prompt)
            if api_result:
                api_result = api_result.strip(' "\'')
                if api_result and api_result.lower() != item_str.lower() and len(api_result) < len(item_str) * 5 + 10:
                    print(f"項目 '{item_str}' 成功翻譯為 '{api_result}' (嘗試 {attempt + 1})")
                    translated_item = api_result
                    break
                else:
                    print(f"項目 '{item_str}' 翻譯結果疑似無效: '{api_result}' (嘗試 {attempt + 1})。可能原因：翻譯與原文相同、格式錯誤或為空。")
            else:
                print(f"項目 '{item_str}' 翻譯 API 調用失敗 (嘗試 {attempt + 1})")
            if attempt < 2:
                print(f"等待 2 秒後重試...")
                time.sleep(2)
        if translated_item:
            translated_items.append(translated_item)
        else:
            print(f"項目 '{item_str}' 翻譯失敗，將使用原始項目")
            translated_items.append(item_str)
    seen = set()
    unique_translated_items = [x for x in translated_items if not (x in seen or seen.add(x))]
    return unique_translated_items

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('detail_static.html')
current_year = datetime.now().year
output_dir = os.path.join('static_site', 'videos')
os.makedirs(output_dir, exist_ok=True)

video_data_list = fetch_top_video_details()
if not video_data_list:
    print("無法從資料庫獲取影片資料，腳本終止。")
    exit()

def sanitize_filename(name):
    name = re.sub(r'[\/*?:".<>|]', '', name)
    name = name.replace(' ', '_')
    return name[:100]

for video_data in video_data_list:
    print(f"\n--- Processing video: {video_data['id']} ---")
    print("Generating AI content...")
    video_title = video_data.get('title', '未知標題')
    video_code = video_data.get('id', 'N/A')
    actress_name = video_data.get('actress', '未知演員')
    genres_list = video_data.get('genres', [])
    base_description = video_data.get('base_info_for_ai', '')
    keywords = ', '.join(genres_list[:3]) if genres_list else '無'
    keywords_en = ', '.join(genres_list[:3]) if genres_list else 'None'
    actress_name_en = actress_name if actress_name != '未知演員' else 'Unknown Actress'
    print(f"開始翻譯影片 {video_data['id']} 的標題、Genres 和 Tags...")
    video_data['genres_en'] = translate_list_to_english(video_data.get('genres', []))
    video_data['tags_en'] = translate_list_to_english(video_data.get('labels', []))
    # --- AI 內容生成 ---
    # 中文 Prompt
    rewrite_title_prompt_zh = f"請將以下影片標題 '{video_title}' 用稍微不同的方式表達，保持意思和長度相似，作為網頁標題使用。"
    print("Rewriting title with AI (Chinese)...")
    raw_ai_rewritten_title_zh = generate_content_with_deepseek(rewrite_title_prompt_zh)
    if "failed" in raw_ai_rewritten_title_zh or not raw_ai_rewritten_title_zh:
        print("AI title rewrite failed (Chinese), using original title.")
        ai_rewritten_title_zh = video_title
    else:
        ai_rewritten_title_zh = raw_ai_rewritten_title_zh.split('\n')[0].strip()
        if not ai_rewritten_title_zh or '(' in ai_rewritten_title_zh:
            print("AI title rewrite resulted in empty/invalid string after processing, using original title.")
            ai_rewritten_title_zh = video_title
    # 僅直接翻譯英文標題，不做 SEO 或多餘內容
    translate_title_prompt_en = f"Translate the following Japanese adult video title strictly into English. Output ONLY the translated title. Do not include the original title, any introductory text, or quotation marks. Just the English translation.\nTitle: '{video_title}'"
    print("Translating title with AI (English)...")
    raw_ai_translated_title_en = generate_content_with_deepseek(translate_title_prompt_en)
    if "failed" in raw_ai_translated_title_en or not raw_ai_translated_title_en:
        print("AI title translation failed (English), using original title.")
        ai_translated_title_en = video_title
    else:
        ai_translated_title_en = raw_ai_translated_title_en.split('\n')[0].strip()
        if not ai_translated_title_en or '(' in ai_translated_title_en:
            print("AI title translation resulted in empty/invalid string after processing, using original title.")
            ai_translated_title_en = video_title
    # 生成 SEO 摘要（移除多餘說明）
    seo_prompt_zh = f"請為以下影片撰寫一段簡短的 SEO meta description (約 50-70 字)，重點強調影片特色和吸引力，包含番號 '{video_code}' 和女優 '{actress_name}'。影片標題：'{video_title}'，類型：{keywords}。請直接輸出描述文字，不要包含字數統計或其他額外說明。"
    print("Generating SEO summary (Chinese)...")
    seo_summary_zh = generate_content_with_deepseek(seo_prompt_zh)
    seo_summary_zh = re.sub(r'\s*\(\d+\s*chars\)$', '', seo_summary_zh).strip()
    seo_prompt_en = f"Write a short SEO meta description (around 50-70 characters) for the following video, highlighting its features and appeal. Include the code '{video_code}' and actress '{actress_name_en}'. Video Title: '{video_title}', Genres: {keywords_en}. Output only the description text."
    print("Generating SEO summary (English)...")
    seo_summary_en = generate_content_with_deepseek(seo_prompt_en)
    seo_summary_en = re.sub(r'\s*\(\d+\s*chars\)$', '', seo_summary_en).strip()

    # 生成中文心得 (女大生觀影心得＋SEO友善＋段落分明)
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
影片標題：'{video_title}'，女優：'{actress_name}'，類型：{keywords}。原始簡介：'{base_description}'"""
    print("Generating review (Chinese - College Girl Style)...")
    ai_content_zh = generate_content_with_deepseek(review_prompt_zh)
    if "failed" in ai_content_zh or not ai_content_zh:
        print("AI review generation failed (Chinese), using placeholder.")
        ai_content_zh = "(AI 心得生成失敗)"

    # 生成英文心得 (Horny College Girl Diary Style, SEO Ready, Low-AI Vibe)
    review_prompt_en = f"""You are a slightly horny, cheeky college girl who writes casual movie notes as late-night diary entries.
Please help me write a review-style note for the JAV movie with code {video_code}.
The tone should be playful, immersive, flirty, and ultra-conversational — like a tweet-thread meets Tumblr fangirl blog.
Structure your writing into these three short but juicy sections:
Why I clicked it – casual intro (like: “I was bored, scrolling, and BAM—this thumbnail hit me” or “a friend dared me to watch this”)
What made me lose my mind – describe 1–2 moments from the scene in emotional/visual detail (moans, positions, how it felt to watch)
Afterthoughts – your emotional state after finishing (ex: “I need a shower,” “lowkey bookmarked it,” “might watch it again tbh”)
Stylistic notes:
Use TikTok-style expressions, emoji, asides (italic comments), and lots of ellipses / line breaks
Aim for 400–600 words, naturally spaced with paragraphs
Avoid AI-sounding vocabulary (make it sound real, slightly chaotic, like horny texting)
You can include hashtags like #Creampie #POV #LateNightRewatch etc.
Video Title: '{ai_translated_title_en}', Actress: '{actress_name_en}', Genres: {keywords_en}. Original Description: '{base_description}'"""
    print("Generating review (English - Horny College Girl Style)...")
    ai_content_en = generate_content_with_deepseek(review_prompt_en)
    if "failed" in ai_content_en or not ai_content_en:
        print("AI review generation failed (English), using placeholder.")
        ai_content_en = "(AI review generation failed)"
    category_links = []
    actress_links = []
    render_data_zh = {
        'lang': 'zh',
        'video': video_data,
        'ai_title': ai_rewritten_title_zh,
        'ai_content': ai_content_zh,
        'seo_summary': seo_summary_zh,
        'category_links': category_links,
        'actress_links': actress_links,
        'breadcrumb_home_link': '../../index_zh.html',
        'current_year': current_year,
        'genres_en': [],
        'tags_en': []
    }
    render_data_en = {
        'lang': 'en',
        'video': video_data,
        'ai_title': ai_translated_title_en,
        'ai_content': ai_content_en,
        'seo_summary': seo_summary_en,
        'category_links': category_links,
        'actress_links': actress_links,
        'breadcrumb_home_link': '../../index_en.html',
        'current_year': current_year,
        'genres_en': video_data.get('genres_en', []),
        'tags_en': video_data.get('tags_en', [])
    }

    # --- 檔案寫入邏輯 --- 
    safe_filename_base = video_data['id'] # 使用 video code 作為基礎檔名

    # 渲染並寫入中文版本
    try:
        html_zh = template.render(**render_data_zh)
        output_path_zh = os.path.join(output_dir, f"{safe_filename_base}_zh.html")
        with open(output_path_zh, 'w', encoding='utf-8') as f:
            f.write(html_zh)
        print(f"中文靜態詳情頁面已產生：{output_path_zh}")
    except Exception as e:
        print(f"寫入中文檔案時發生錯誤 ({output_path_zh}): {e}")

    # 渲染並寫入英文版本
    try:
        html_en = template.render(**render_data_en)
        output_path_en = os.path.join(output_dir, f"{safe_filename_base}_en.html")
        with open(output_path_en, 'w', encoding='utf-8') as f:
            f.write(html_en)
        print(f"英文靜態詳情頁面已產生：{output_path_en}")
    except Exception as e:
        print(f"寫入英文檔案時發生錯誤 ({output_path_en}): {e}")

print("\n所有影片詳情頁面處理完成！")