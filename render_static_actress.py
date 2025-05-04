import os
import mysql.connector
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import re # 用於生成安全的文件名

# --- 資料庫連接資訊 (從 render_static_detail.py 複製) ---
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

# --- 資料庫操作函數 --- 
def get_db_connection():
    """建立並返回資料庫連接"""
    try:
        conn = mysql.connector.connect(**connection_config)
        print("資料庫連接成功")
        return conn
    except Exception as e:
        print(f"資料庫連接錯誤: {e}")
        return None

def fetch_actresses_with_videos():
    """從資料庫獲取所有女優及其參演的影片列表 (code 和 title)"""
    conn = get_db_connection()
    if not conn:
        return {}
    actress_videos = {}
    try:
        cursor = conn.cursor(dictionary=True)
        # 查詢所有女優，並通過 video_actress 和 videos 表連接獲取影片的 code 和 title
        query = """
            SELECT
                a.id AS actress_id,
                a.name AS actress_name,
                v.code AS video_code,
                v.title AS video_title
            FROM actresses a
            JOIN video_actress va ON a.id = va.actress_id
            JOIN videos v ON va.video_id = v.id
            ORDER BY a.name, v.release_date DESC # 按女優名稱排序，影片按日期降序
        """
        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            print(f"從資料庫成功獲取 {len(results)} 條女優-影片關聯記錄")
            for row in results:
                actress_id = row['actress_id']
                actress_name = row['actress_name']
                video_info = {'code': row['video_code'], 'title': row['video_title']}

                if actress_name not in actress_videos:
                    actress_videos[actress_name] = []
                # 檢查影片是否已存在 (避免重複，雖然理論上 JOIN 不會重複)
                if video_info not in actress_videos[actress_name]:
                     actress_videos[actress_name].append(video_info)
        else:
            print("在資料庫中找不到任何女優或影片關聯")

    except mysql.connector.Error as err:
        print(f"查詢女優及其影片時發生錯誤: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")
    return actress_videos

# --- 輔助函數：生成安全的文件名 ---
def sanitize_filename(name):
    """將名稱轉換為安全的文件名"""
    # 移除或替換不安全字符
    name = re.sub(r'[\/*?:".<>|]', '', name)
    # 將空格替換為下劃線
    name = name.replace(' ', '_')
    # 限制長度 (可選)
    return name[:100] # 限制文件名長度為 100

# --- 設定 Jinja2 ---
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('actress_static.html')

# --- 獲取資料 ---
print("Fetching actress and video data from database...")
actress_data = fetch_actresses_with_videos()

if not actress_data:
    print("無法從資料庫獲取女優資料，腳本終止。")
    exit()

# --- 遍歷女優資料並生成頁面 ---
# Define the output directory for static site actress pages
output_dir = os.path.join('static_site', 'actresses')
os.makedirs(output_dir, exist_ok=True)

current_year = datetime.now().year

for actress_name, videos in actress_data.items():
    print(f"\n--- Processing actress: {actress_name} ---")
    safe_filename_base = sanitize_filename(actress_name)

    # 準備模板渲染的數據
    # Adjust video links to point to the static video directory
    adjusted_videos = []
    for video in videos:
        adjusted_videos.append({
            'code': video['code'],
            'title': video['title'],
            # Relative path from static_site/actresses/ to static_site/videos/
            'link_zh': f"../../videos/{video['code']}_zh.html",
            'link_en': f"../../videos/{video['code']}_en.html"
        })

    render_data = {
        'actress_name': actress_name,
        'videos': adjusted_videos, # 使用調整過連結的影片列表
        'current_year': current_year
    }

    # 渲染中文版本
    render_data['lang'] = 'zh'
    # Add breadcrumb link to static index
    render_data['breadcrumb_home_link'] = '../../index_zh.html'
    html_zh = template.render(**render_data)
    output_path_zh = os.path.join(output_dir, f"{safe_filename_base}_zh.html")
    try:
        with open(output_path_zh, 'w', encoding='utf-8') as f:
            f.write(html_zh)
        print(f"中文靜態女優頁面已產生：{output_path_zh}")
    except Exception as e:
        print(f"寫入中文檔案時發生錯誤 ({output_path_zh}): {e}")

    # 渲染英文版本
    render_data['lang'] = 'en'
    # Add breadcrumb link to static index
    render_data['breadcrumb_home_link'] = '../../index_en.html'
    html_en = template.render(**render_data)
    output_path_en = os.path.join(output_dir, f"{safe_filename_base}_en.html")
    try:
        with open(output_path_en, 'w', encoding='utf-8') as f:
            f.write(html_en)
        print(f"英文靜態女優頁面已產生：{output_path_en}")
    except Exception as e:
        print(f"寫入英文檔案時發生錯誤 ({output_path_en}): {e}")

print("\n所有女優頁面處理完成！")