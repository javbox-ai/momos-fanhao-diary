import os
import json # Not strictly needed for this version, but good for future data loading
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

# --- Configuration ---
NUM_TEST_VIDEOS = 10
# BASE_URL should ideally be loaded from .env or a config file
# For OG tags, an absolute URL is preferred.
# Using the one from your .env.example:
BASE_URL = "https://javbox-ai.github.io/momos-fanhao-diary" 
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
OUTPUT_DIR_BASE = os.path.join(PROJECT_ROOT, 'output', 'videos')

# --- Mock Data Generation ---
def get_mock_videos(count):
    """Generates a list of mock video data."""
    videos = []
    for i in range(1, count + 1):
        fanhao = f"TEST-{str(i).zfill(3)}"
        video_data = {
            'id': fanhao,
            'fanhao': fanhao,
            'actress_cn': f'测试女優 {i}',
            'actress_en': f'Test Actress {i}',
            'actress_slug': f'test-actress-{i}', # Generic slug for URL building
            'ai_title_cn': f'AI生成中文标题 {i} - {fanhao}',
            'ai_title_en': f'AI Generated English Title {i} - {fanhao}',
            
            'og_image_url': f'/static/images/placeholder_og_video.png', # General placeholder
            'cover_image_url_blurred': f'/static/images/placeholder_cover_blurred.png', 
            'cover_image_url_clear': f'/static/images/placeholder_cover_clear.png',
            
            'release_date': f'2024-01-{str(i).zfill(2)}',
            
            'genres': [
                {'name_cn': '劇情片', 'name_en': 'Drama', 'slug': 'drama'},
                {'name_cn': '可愛風', 'name_en': 'Cute Style', 'slug': 'cute'}
            ],
            'tags': [
                {'name_cn': '高清画质', 'name_en': 'HD Quality'},
                {'name_cn': '短发造型', 'name_en': 'Short Hair'}
            ],
            'ai_review_cn': f'<p>这是关于 {fanhao} ({f"测试女優 {i}"}) 的AI生成的<b>中文</b>观影心得。这部影片的AI标题是"{f"AI生成中文标题 {i} - {fanhao}"}"。</p><p>心得内容段落二，充满细节与情感。 #成人影片 #中文心得 #{f"测试女優{i}"}</p>',
            'ai_review_en': f'<p>This is an AI generated <b>English</b> viewing experience for {fanhao} ({f"Test Actress {i}"}). The AI title for this one is "{f"AI Generated English Title {i} - {fanhao}"}".</p><p>Review content paragraph two, full of details and emotion. #AdultFilm #EnglishReview #{f"TestActress{i}"}</p>',
            
            'seo_meta_description_cn': f'{fanhao} 由 {f"测试女優 {i}"} 主演。AI重写标题："{f"AI生成中文标题 {i} - {fanhao}"}"。亮点：精彩剧情，不容错过。片长：12{i}分钟。',
            'seo_meta_description_en': f'{fanhao} starring {f"Test Actress {i}"}. AI Rewritten Title: "{f"AI Generated English Title {i} - {fanhao}"}"。Highlights: Great plot, must watch. Duration: 12{i} minutes.',

            'plot_summary_cn': f'{fanhao} ({f"AI生成中文标题 {i} - {fanhao}"}) 的中文剧情概要，包含一些引人入胜的细节，主要围绕主角 {f"测试女優 {i}"} 展开。',
            'plot_summary_en': f'English plot summary for {fanhao} ({f"AI Generated English Title {i} - {fanhao}"}), with engaging details focusing on the main actress, {f"Test Actress {i}"}.',
        }
        videos.append(video_data)
    return videos

# --- Jinja2 Environment Setup ---
def setup_jinja_env():
    """Sets up and returns the Jinja2 environment."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True, # Enable autoescaping for security with HTML
        trim_blocks=True, # Remove first newline after a block
        lstrip_blocks=True # Strip leading spaces from line to block start
    )
    # Add 'now' filter for `{{ "now"|date("Y") }}` in templates
    env.filters['date'] = lambda fmt: datetime.utcnow().strftime(fmt)
    return env

# --- Page Generation Logic ---
def generate_video_detail_pages(jinja_env, videos_data):
    """Generates detail pages for each video in both languages."""
    template = jinja_env.get_template('detail_static.html')

    if not os.path.exists(OUTPUT_DIR_BASE):
        os.makedirs(OUTPUT_DIR_BASE)
        print(f"Created directory: {OUTPUT_DIR_BASE}")

    generated_files_count = 0
    for video_data in videos_data:
        fanhao = video_data['fanhao']
        
        for lang_variant in ['zh', 'en']: # 'zh' for Chinese, 'en' for English page
            
            context = {}
            # Determine current language for the template ('cn' or 'en')
            current_template_lang = 'cn' if lang_variant == 'zh' else 'en'
            context['lang'] = current_template_lang

            # Prepare video data for the template
            # The template uses constructs like `video.actress_cn if lang == 'cn' else video.actress_en`
            # So, the full video_data can be passed.
            context['video'] = video_data.copy() # Pass a copy

            # Dynamically create URLs for actress and genres based on current language
            # These would link to actress pages and category pages if they exist
            actress_slug = video_data['actress_slug']
            context['video']['actress_url'] = f"/actress/{actress_slug}_{current_template_lang}.html"
            
            processed_genres = []
            for g in video_data['genres']:
                genre_slug = g['slug']
                processed_genres.append({
                    'name_cn': g['name_cn'],
                    'name_en': g['name_en'],
                    'url': f"/category/{genre_slug}_{current_template_lang}.html"
                })
            context['video']['genres'] = processed_genres
            
            # SEO related context
            context['seo'] = {
                'meta_description_cn': video_data['seo_meta_description_cn'],
                'meta_description_en': video_data['seo_meta_description_en'],
                # title and og:title are largely constructed within detail_static.html using video data
            }

            # Current page URL (for og:url) and alternate language page URL
            current_page_relative_url = f"/videos/{fanhao}_{lang_variant}.html"
            context['current_page_url'] = BASE_URL.rstrip('/') + current_page_relative_url
            
            if lang_variant == 'zh':
                alternate_lang_page_code = 'en'
            else: # lang_variant == 'en'
                alternate_lang_page_code = 'zh'
            context['alternate_lang_url'] = f"/videos/{fanhao}_{alternate_lang_page_code}.html"
            
            # Render the template
            html_content = template.render(context)

            # Write the rendered HTML to file
            output_filename = f"{fanhao}_{lang_variant}.html"
            output_filepath = os.path.join(OUTPUT_DIR_BASE, output_filename)
            
            try:
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                # print(f"Generated: {output_filepath}")
                generated_files_count += 1
            except IOError as e:
                print(f"Error writing file {output_filepath}: {e}")
    
    print(f"Successfully generated {generated_files_count} video detail pages in '{OUTPUT_DIR_BASE}'.")

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting static video page generation...")
    
    mock_video_list = get_mock_videos(NUM_TEST_VIDEOS)
    jinja_environment = setup_jinja_env()
    
    generate_video_detail_pages(jinja_environment, mock_video_list)
    
    print("Static video page generation complete.") 