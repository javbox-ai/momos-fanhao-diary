from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, abort
import requests
import os
import random # 新增
from datetime import datetime # 新增

# --- 配置 --- 
# !! 請從環境變數或安全的設定檔讀取您的 DeepSeek API Key !!
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'YOUR_DEEPSEEK_API_KEY_HERE') # 警告：請勿直接將 Key 寫在此處
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', "https://api.deepseek.com/v1/chat/completions") # 確認 DeepSeek API 端點

# !! 資料庫連接資訊 !!
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'yoyo0024'),
    'database': os.getenv('DB_DATABASE', 'missav_db')
}

# 使用 mysql.connector (MySQL)
connection_config = {
    'user': DATABASE_CONFIG['user'],
    'password': DATABASE_CONFIG['password'],
    'host': DATABASE_CONFIG['host'],
    'database': DATABASE_CONFIG['database']
}

# 選擇您要使用的資料庫連接庫
# import pyodbc # For SQL Server/ODBC
import mysql.connector # For MySQL
# import psycopg2 # For PostgreSQL
from datetime import datetime # 新增

app = Flask(__name__)

# 獲取 app.py 所在的目錄
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# 獲取 app.py 所在的目錄
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# 更新：指向包含分類頁面的子目錄
STATIC_PAGES_DIR = os.path.join(APP_ROOT, 'output') # 指向 output 目錄

# --- 資料庫操作函數 (待實作) ---
def get_db_connection():
    """建立並返回資料庫連接"""
    try:
        # 使用 mysql.connector (如果您的資料庫是 MySQL)
        conn = mysql.connector.connect(**connection_config)
        print("資料庫連接成功")
        return conn
    except Exception as e:
        print(f"資料庫連接錯誤: {e}")
        return None

# User's desired categories
DESIRED_CATEGORIES = [
    "巨乳", "素人", "熟女", "騎乘", "女高中生", "潮吹", "乳交", "自拍",
    "痴女", "偷拍", "戀物癖", "NTR", "自慰", "拘束", "羞辱", "角色扮演",
    "女同性戀", "OL", "制服", "不倫", "肛門", "舔陰", "小隻馬", "SM",
    "按摩", "綑綁", "M男", "戀足"
]

def fetch_all_genres():
    """從資料庫獲取所有唯一的類型名稱"""
    conn = get_db_connection()
    if not conn:
        return []
    genres = []
    try:
        cursor = conn.cursor()
        query = "SELECT DISTINCT name FROM genres ORDER BY name ASC"
        cursor.execute(query)
        # 將元組列表轉換為字串列表
        genres = [item[0] for item in cursor.fetchall()]
        print(f"從資料庫成功獲取 {len(genres)} 個分類")
    except mysql.connector.Error as err:
        print(f"查詢所有分類時發生錯誤: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")
    return genres

def fetch_latest_reviews(limit=10):
    """從資料庫獲取最新影片 (依發行日排序)"""
    conn = get_db_connection()
    if not conn:
        return []
    reviews = []
    try:
        cursor = conn.cursor(dictionary=True) # 使用字典游標
        # 查詢 videos 表，按 release_date 降序排列，限制數量
        # 選擇需要的欄位，注意欄位名稱映射 (code -> id, cover_url -> cover_image)
        query = """
            SELECT
                v.code AS id,
                v.title,
                v.cover_url AS cover_image,
                v.description AS summary, # 使用 description 作為 summary
                GROUP_CONCAT(DISTINCT a.name) AS actress # 獲取女優名
            FROM videos v
            LEFT JOIN video_actress va ON v.id = va.video_id
            LEFT JOIN actresses a ON va.actress_id = a.id
            GROUP BY v.id
            ORDER BY v.release_date DESC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        reviews = cursor.fetchall()
        # 處理 cover_image URL，如果為空則使用預設圖
        for review in reviews:
            if not review['cover_image']:
                review['cover_image'] = url_for('static', filename='placeholder.jpg')
            # 將 actress 字串分割成列表 (如果需要)
            if review['actress']:
                review['actress'] = review['actress'].split(',')
            else:
                review['actress'] = []

        print(f"從資料庫成功獲取 {len(reviews)} 篇最新心得")
    except mysql.connector.Error as err:
        print(f"查詢最新心得時發生錯誤: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")
    return reviews

def fetch_video_detail(video_code):
    """從資料庫獲取特定影片的詳細資訊 (使用 video code)"""
    conn = get_db_connection()
    if not conn:
        return None
    video_detail = None
    try:
        cursor = conn.cursor(dictionary=True)
        # 根據 code 查詢 videos 表，並連接其他相關表獲取完整資訊
        query = """
            SELECT
                v.code AS id, # 使用 code 作為 id
                v.title,
                v.cover_url AS cover_image,
                v.description, # 原始簡介
                v.release_date,
                GROUP_CONCAT(DISTINCT a.name) AS actresses, # 獲取所有女優名
                GROUP_CONCAT(DISTINCT g.name) AS genres,    # 獲取所有類型名
                GROUP_CONCAT(DISTINCT s.name) AS series,    # 獲取所有系列名
                GROUP_CONCAT(DISTINCT l.name) AS labels     # 獲取所有標籤名
            FROM videos v
            LEFT JOIN video_actress va ON v.id = va.video_id
            LEFT JOIN actresses a ON va.actress_id = a.id
            LEFT JOIN video_genre vg ON v.id = vg.video_id
            LEFT JOIN genres g ON vg.genre_id = g.id
            LEFT JOIN video_series vs ON v.id = vs.video_id
            LEFT JOIN series s ON vs.series_id = s.id
            LEFT JOIN video_label vl ON v.id = vl.video_id
            LEFT JOIN labels l ON vl.label_id = l.id
            WHERE v.code = %s
            GROUP BY v.id
        """
        cursor.execute(query, (video_code,))
        video_detail = cursor.fetchone()

        if video_detail:
            print(f"從資料庫成功獲取影片 {video_code} 的詳細資訊")
            # 處理空值和轉換格式
            if not video_detail['cover_image']:
                video_detail['cover_image'] = url_for('static', filename='placeholder.jpg')
            # 將逗號分隔的字串轉換為列表
            for key in ['actresses', 'genres', 'series', 'labels']:
                if video_detail[key]:
                    video_detail[key] = video_detail[key].split(',')
                else:
                    video_detail[key] = []
            # 將 release_date 轉換為字串 (如果需要特定格式)
            if video_detail['release_date']:
                 video_detail['release_date'] = video_detail['release_date'].strftime('%Y-%m-%d')
            else:
                 video_detail['release_date'] = 'N/A'
            # 為了與模板兼容，將 actresses 列表的第一個元素賦給 actress (如果存在)
            video_detail['actress'] = video_detail['actresses'][0] if video_detail['actresses'] else None
            # 為了與模板兼容，將 genres 賦給 tags
            video_detail['tags'] = video_detail['genres']
            # 準備 AI prompt 需要的基礎資訊 (例如 description)
            video_detail['base_info_for_ai'] = video_detail.get('description', '')

        else:
            print(f"在資料庫中找不到影片 {video_code}")

    except mysql.connector.Error as err:
        print(f"查詢影片 {video_code} 詳細資訊時發生錯誤: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")
    return video_detail

def fetch_category_articles(category_name, limit=20):
    """從資料庫獲取特定類別 (genre) 的影片"""
    conn = get_db_connection()
    if not conn:
        return []
    articles = []
    try:
        cursor = conn.cursor(dictionary=True)
        # 根據 genre 名稱查詢 videos
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

        # 處理 cover_image 和 actress
        for article in articles:
            if not article['cover_image']:
                article['cover_image'] = url_for('static', filename='placeholder.jpg')
            if article['actress']:
                article['actress'] = article['actress'].split(',')
            else:
                article['actress'] = []

        print(f"從資料庫成功獲取類別 '{category_name}' 的 {len(articles)} 篇文章")
    except mysql.connector.Error as err:
        print(f"查詢類別 '{category_name}' 文章時發生錯誤: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")
    return articles

# --- DeepSeek API 互動函數 ---
def generate_seo_content(prompt, lang='zh'):
    """使用 DeepSeek API 生成 SEO 優化內容"""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == 'YOUR_DEEPSEEK_API_KEY_HERE':
        print("警告：未設定 DeepSeek API Key 或仍使用預留位置。返回範例文字。")
        if lang == 'en':
            return "(Sample) This is a sample SEO summary generated for preview purposes because API key is not configured."
        else:
            return "(範例) 這是為了預覽目的而生成的範例 SEO 摘要，因為 API 金鑰未設定。"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
    }

    data = {
        "model": "deepseek-chat", # 或您想使用的模型
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that generates SEO content."}, 
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 150, # 根據需要調整
        "temperature": 0.7 # 根據需要調整
    }

    try:
        print(f"正在呼叫 DeepSeek API ({lang})...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30) # 增加超時
        response.raise_for_status()  # 如果狀態碼不是 2xx，則引發 HTTPError
        
        result = response.json()
        # 根據 DeepSeek API 的實際回應格式提取內容
        # 假設回應格式為 {'choices': [{'message': {'content': '...'}}]}
        if result.get('choices') and result['choices'][0].get('message'):
            content = result['choices'][0]['message'].get('content', '').strip()
            print(f"DeepSeek API 成功返回內容 ({lang})")
            return content
        else:
            print(f"DeepSeek API 回應格式不符或無內容 ({lang}): {result}")
            return f"(Error: Unexpected API response format - {lang})"

    except requests.exceptions.RequestException as e:
        print(f"呼叫 DeepSeek API 時發生錯誤 ({lang}): {e}")
        return f"(Error: API request failed - {lang})"
    except Exception as e:
        print(f"處理 DeepSeek API 回應時發生未知錯誤 ({lang}): {e}")
        return f"(Error: Unknown error processing API response - {lang})"

# --- Helper Functions for Static Pages ---
def get_latest_static_pages(limit=10, lang='zh'):
    """獲取 output 目錄下最新的靜態詳情頁面"""
    pages = []
    try:
        # 確保 STATIC_PAGES_DIR 指向 output 目錄
        if not os.path.exists(STATIC_PAGES_DIR) or not os.path.isdir(STATIC_PAGES_DIR):
            print(f"Static pages directory not found: {STATIC_PAGES_DIR}")
            return []

        # 遍歷 output 目錄下的所有 HTML 文件
        for filename in os.listdir(STATIC_PAGES_DIR):
            # 過濾掉分類頁面和其他非詳情頁
            # 假設詳情頁格式為 ID_lang.html (例如 abf-123_zh.html)
            # 這裡需要一個更可靠的方式來識別詳情頁，例如檢查文件名模式
            # 暫時我們先假設所有符合 *_lang.html 模式的都是（這會包含分類頁，需要改進）
            if filename.endswith(f'_{lang}.html') and not filename.startswith('index_') and not filename.startswith('category_'):
                file_path = os.path.join(STATIC_PAGES_DIR, filename)
                if os.path.isfile(file_path):
                    try:
                        mtime = os.path.getmtime(file_path)
                        # 從檔名提取顯示名稱 (去除語言後綴和 .html)
                        display_name = filename.replace(f'_{lang}.html', '')
                        pages.append({
                            'url': filename, # 相對路徑
                            'display_name': display_name,
                            'mtime': datetime.fromtimestamp(mtime),
                            'lang': lang
                        })
                    except Exception as e:
                        print(f"Error processing file {filename}: {e}")

        # 按修改時間降序排序
        pages.sort(key=lambda x: x['mtime'], reverse=True)
        print(f"Found {len(pages)} static pages for lang '{lang}' in {STATIC_PAGES_DIR}")
        return pages[:limit]

    except Exception as e:
        print(f"Error accessing static pages directory {STATIC_PAGES_DIR}: {e}")
        return []

def get_top_favorites_static(limit=5, lang='zh'):
    """獲取最受歡迎的靜態頁面 (模擬)"""
    # 在實際應用中，這可能來自日誌分析、計數器等
    # 這裡我們只是從現有靜態頁面中隨機選擇
    all_static_pages = get_latest_static_pages(limit=100, lang=lang) # 獲取更多頁面以供選擇
    if not all_static_pages:
        return []
    # 確保選擇數量不超過實際頁面數
    actual_limit = min(limit, len(all_static_pages))
    return random.sample(all_static_pages, actual_limit)

# --- Flask 路由 ---

# --- 路由 --- 
@app.route('/')
@app.route('/index_<lang>.html') # 處理靜態首頁請求
def index(lang='zh'): # 預設語言為中文
    # 獲取最新的靜態頁面列表 (從 output 目錄)
    latest_static_pages = get_latest_static_pages(limit=10, lang=lang) # Restore original call
    # 獲取最受歡迎的靜態頁面 (模擬或從日誌分析)
    top_5_favorites = get_top_favorites_static(limit=5, lang=lang) # 假設有此函數

    # 獲取所有分類 (從資料庫或緩存)
    # all_genres = fetch_all_genres() # 改為使用預設分類
    all_genres = DESIRED_CATEGORIES # 使用用戶指定的分類列表

    return render_template('index.html', 
                           latest_static_pages=latest_static_pages,
                           all_genres=all_genres,
                           top_5_favorites=top_5_favorites, # 傳遞最愛列表
                           lang=lang)

@app.route('/search_redirect')
def search_redirect():
    """處理來自頁首搜尋框的重新導向"""
    query = request.args.get('q', '')
    lang = request.args.get('lang', 'zh')
    # 重新導向到 /go 路由，並帶上搜尋參數
    return redirect(url_for('go_redirect', query=query, lang=lang))

@app.route('/go')
def go_redirect():
    """顯示廣告跳轉頁面"""
    query = request.args.get('query', '') # 從 URL 獲取搜尋關鍵字
    lang = request.args.get('lang', 'zh') # 從 URL 獲取語言
    # 渲染 go.html 模板，並傳遞搜尋關鍵字和語言
    return render_template('go.html', query=query, lang=lang)
# --- 新增：獲取靜態頁面資訊 ---
def get_static_pages(directory=STATIC_PAGES_DIR):
    """掃描指定目錄，獲取 HTML 檔案列表及其修改時間"""
    pages = []
    abs_directory = os.path.abspath(directory) # 獲取絕對路徑
    if not os.path.exists(abs_directory):
        print(f"警告：靜態頁目錄 '{abs_directory}' 不存在。")
        return pages

    try:
        for filename in os.listdir(abs_directory):
            if filename.endswith(".html"):
                file_path = os.path.join(abs_directory, filename)
                try:
                    mtime = os.path.getmtime(file_path)
                    # 從檔名解析資訊 (假設格式為 category_lang.html)
                    parts = filename.replace('.html', '').split('_')
                    lang = parts[-1] if len(parts) > 1 and parts[-1] in ['zh', 'en'] else 'unknown'
                    category_name = '_'.join(parts[:-1]) if lang != 'unknown' else '_'.join(parts)
                    # 替換回原始空格和斜線 (如果需要更友好的顯示名稱)
                    # 注意：這依賴於 render_static_category.py 中的命名方式
                    display_name = category_name.replace('_', ' ')
                                            # .replace('/', '/') # 如果有替換斜線，還原它

                    pages.append({
                        'filename': filename,
                        # 'path': file_path, # 完整路徑通常不需要傳到前端
                        # 使用新的路由生成 URL
                        'url': url_for('static_page_serve', filename=filename, _external=False), # Use new function name
                        'mtime': datetime.fromtimestamp(mtime),
                        'display_name': display_name, # 用於顯示的名稱
                        'lang': lang
                    })
                except OSError as e:
                    print(f"讀取檔案 '{file_path}' 資訊時出錯: {e}")
                except Exception as e: # 捕捉 url_for 可能的錯誤 (雖然在此處不太可能)
                    print(f"處理檔案 '{filename}' 時發生錯誤: {e}")
    except OSError as e:
        print(f"讀取目錄 '{abs_directory}' 時出錯: {e}")

    print(f"從 '{abs_directory}' 成功掃描到 {len(pages)} 個靜態頁面")
    return pages

@app.route('/detail/<string:video_code>') # 改為接收 string 類型的 video_code
def detail(video_code):
    lang = request.args.get('lang', 'zh')
    video_data = fetch_video_detail(video_code) # 移除 lang 參數

    if not video_data:
        # Handle case where video is not found (e.g., render a 404 page or redirect)
        # For now, return a simple message
        return f"Video with ID {video_id} not found.", 404

    # --- Generate AI Content using DeepSeek --- 
    # Prepare prompts based on video data and language
    # You might want to customize these prompts further
    title = video_data.get('title', '') # Use the language-specific title fetched
    # 使用從資料庫獲取的 description 作為基礎資訊
    base_info = video_data.get('base_info_for_ai', '') 

    # Prompt for AI Introduction
    intro_prompt_zh = f"請根據以下資訊，為影片 '{title}' 產生一段吸引人的中文介紹文字，著重於其特色與看點：\n{base_info}"
    intro_prompt_en = f"Based on the following information, generate an engaging English introduction for the video '{title}', focusing on its features and highlights:\n{base_info}"
    ai_intro = generate_seo_content(intro_prompt_en if lang == 'en' else intro_prompt_zh, lang)

    # Prompt for AI Review
    review_prompt_zh = f"請根據以下資訊，為影片 '{title}' 撰寫一段深入的中文觀後心得，包含情節、演員表現或風格評論：\n{base_info}"
    review_prompt_en = f"Based on the following information, write an in-depth English review for the video '{title}', including comments on the plot, actor performance, or style:\n{base_info}"
    ai_review = generate_seo_content(review_prompt_en if lang == 'en' else review_prompt_zh, lang)

    # Prompt for SEO Summary (Meta Description)
    seo_prompt_zh = f"請為影片 '{title}' 產生一段約 150 字元的中文 SEO 摘要，包含主要關鍵字，用於網頁 meta description。"
    seo_prompt_en = f"Generate a concise English SEO summary (around 150 characters) for the video '{title}', including main keywords, suitable for a webpage meta description."
    seo_summary = generate_seo_content(seo_prompt_en if lang == 'en' else seo_prompt_zh, lang)
    # --- End AI Content Generation ---

    return render_template('detail.html', 
                           video=video_data, 
                           ai_intro=ai_intro, 
                           ai_review=ai_review, 
                           seo_summary=seo_summary, 
                           lang=lang)

@app.route('/category/<string:category_name>')
def category(category_name):
    lang = request.args.get('lang', 'zh')
    articles = fetch_category_articles(category_name) # 移除 lang 參數
    # TODO: 從資料庫獲取分類列表
    # categories = fetch_categories()
    return render_template('category.html', category_name=category_name, articles=articles, lang=lang)

    # Or redirect to a dedicated search results page:
    # return redirect(url_for('search_results', lang=lang, q=query))
    
    # Placeholder: Redirecting back to index for now
    # TODO: Implement actual search logic and results page
    latest_reviews = fetch_latest_reviews(lang) # Fetch reviews for the target language's index
    return render_template('index.html', latest_reviews=latest_reviews, lang=lang, search_query=query)


# --- 應用程式啟動 --- 
if __name__ == '__main__':
    # 使用環境變數 PORT，若無則預設為 5000
    port = int(os.environ.get('PORT', 5000))
    # 監聽所有網路介面，方便從外部訪問 (例如 Docker 容器)
    app.run(host='0.0.0.0', port=port, debug=True) # 開啟 debug 模式方便開發

# 提供靜態頁面 (例如分類頁面、詳情頁面)
@app.route('/static_pages/<filename>')
def static_page_serve(filename): # Renamed function for clarity
    # 從相對於 app.py 的 'output' 目錄提供檔案
    # Use the relative path defined in STATIC_PAGES_DIR
    # Flask's send_from_directory should resolve this relative to app.root_path
    print(f"Attempting to serve static file: {filename} from directory: {STATIC_PAGES_DIR}") # Add logging
    try:
        # Use absolute path (now points to output/categories)
        print(f"Serving file '{filename}' from absolute directory: {STATIC_PAGES_DIR}") # More logging
        return send_from_directory(STATIC_PAGES_DIR, filename)
    except FileNotFoundError:
        # Log the absolute directory path used
        print(f"Error: File not found - {filename} in absolute directory: {STATIC_PAGES_DIR}")
        abort(404)

# --- 錯誤處理 ---
@app.errorhandler(404)
def page_not_found(e):
    # 嘗試從請求參數獲取語言，否則預設為中文
    lang = request.args.get('lang', 'zh') 
    return render_template('404.html', lang=lang), 404

# --- 靜態頁面服務 (更新) ---
@app.route('/output/<path:filename>')
def serve_static_page(filename):
    # 檢查檔案是否存在
    if not os.path.exists(os.path.join(STATIC_PAGES_DIR, filename)):
        # 如果檔案不存在，返回 404 錯誤頁面
        # 嘗試從檔名解析語言，否則預設
        lang_match = re.search(r'_(zh|en)\.html$', filename)
        lang = lang_match.group(1) if lang_match else 'zh'
        return render_template('404.html', lang=lang), 404
    return send_from_directory(STATIC_PAGES_DIR, filename)

# --- 啟動應用 --- 
if __name__ == '__main__':
    # 確保 output 目錄存在
    os.makedirs(STATIC_PAGES_DIR, exist_ok=True)
    # 運行 Flask 應用
    # 注意：debug=True 不應在生產環境中使用
    app.run(debug=True, host='0.0.0.0') # 監聽所有接口，方便局域網訪問