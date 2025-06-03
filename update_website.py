import os
import re
import glob
from bs4 import BeautifulSoup
from pathlib import Path

# 分類名稱翻譯字典
CATEGORY_TRANSLATIONS = {
    "單體作品": "Solo Work",
    "多人運動": "Group Sex",
    "強制口交": "Forced Oral",
    "獨家": "Exclusive",
    "羞辱": "Humiliation",
    "薄格": "Mosaic",
    "高清": "HD",
    "巨乳": "Big Boobs",
    "人妻": "Married Woman",
    "中出": "Creampie",
    "熟女": "Mature Woman",
    "美少女": "Beautiful Girl",
    "痴女": "Slut",
    "騎乘": "Cowgirl",
    "NTR": "NTR",
    "潮吹": "Squirting",
    "超薄格": "Light Mosaic",
    "苗條": "Slender",
    "企劃": "Planning",
    "劇情": "Drama",
    "淫亂": "Lewd",
    "口交": "Blowjob",
    "3P、4P": "Threesome/Foursome",
    "69": "69",
    "OL": "Office Lady",
    "主觀視角": "POV",
    "亂交": "Orgy",
    "合集": "Collection"
}

def fix_website_title(html_content):
    """修正網站標題，移除重複的MOMO"""
    # 修正<title>標籤中的網站名稱
    html_content = re.sub(r'<title>(.*?)MOMO MOMO(.*?)</title>', r'<title>\1MOMO\2</title>', html_content)
    
    # 修正meta標籤中的網站名稱
    html_content = re.sub(r'content="(.*?)MOMO MOMO(.*?)"', r'content="\1MOMO\2"', html_content)
    
    # 修正og:site_name中的網站名稱
    html_content = re.sub(r'content="MOMO MOMO Fanhao Diary"', r'content="MOMO Fanhao Diary"', html_content)
    
    return html_content

def optimize_review_paragraphs(html_content):
    """優化觀影心得段落，使用<p>標籤包裹每個段落"""
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 尋找中文觀影心得
    review_content_divs = soup.select('.ai-review .review-content')
    for div in review_content_divs:
        # 已經有<p>標籤的情況下，確保每個段落都正確包裹
        if div.find('p'):
            # 檢查是否有需要分段的長段落
            for p in div.find_all('p'):
                if len(p.get_text()) > 300 and '<br>' in str(p):
                    # 切割段落
                    paragraphs = str(p).split('<br>')
                    # 清除原有內容
                    p.clear()
                    # 重新加入分段後的內容
                    for para in paragraphs:
                        if para.strip():
                            new_p = soup.new_tag('p')
                            new_p.string = BeautifulSoup(para, 'html.parser').get_text().strip()
                            p.insert_before(new_p)
                    p.decompose()  # 移除原始的空<p>標籤
        else:
            # 沒有<p>標籤的情況，將文本內容切分為段落
            text = div.get_text()
            # 清除原有內容
            div.clear()
            
            # 按句號或換行符切割段落
            paragraphs = re.split(r'(?<=[。！？.!?])\s*(?=\S)|(?<=\n)', text)
            
            # 合併太短的段落
            merged_paragraphs = []
            current_paragraph = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                    
                if len(current_paragraph) < 100:
                    if current_paragraph:
                        current_paragraph += " " + para
                    else:
                        current_paragraph = para
                else:
                    if current_paragraph:
                        merged_paragraphs.append(current_paragraph)
                    current_paragraph = para
            
            if current_paragraph:
                merged_paragraphs.append(current_paragraph)
            
            # 添加<p>標籤
            for para in merged_paragraphs:
                p = soup.new_tag('p')
                p.string = para
                div.append(p)
    
    # 尋找英文觀影心得
    en_review_content_divs = soup.select('.ai-review .review-content')
    for div in en_review_content_divs:
        # 檢查是否為英文心得（簡單地檢查是否有大量英文字符）
        text = div.get_text()
        if len(re.findall(r'[a-zA-Z]', text)) > len(text) * 0.5:  # 如果超過50%是英文字符
            div['class'] = div.get('class', []) + ['english-review']
            
            # 檢查是否已經有<p>標籤
            if not div.find('p'):
                # 清除原有內容
                original_content = str(div)
                div.clear()
                
                # 按照markdown風格的段落分隔符號切割
                paragraphs = re.split(r'\n\s*\n|\n---\n', original_content)
                
                for para in paragraphs:
                    if para.strip():
                        p = soup.new_tag('p')
                        p_content = BeautifulSoup(para, 'html.parser')
                        
                        # 處理標題
                        headers = p_content.find_all(re.compile(r'^h[1-6]$'))
                        for header in headers:
                            h = soup.new_tag(header.name)
                            h.string = header.get_text()
                            div.append(h)
                            header.decompose()
                        
                        # 處理剩餘文本
                        p.append(p_content)
                        div.append(p)
    
    return str(soup)

def translate_categories_and_actresses(html_content):
    """翻譯英文版頁面中的分類和女優名稱"""
    for zh, en in CATEGORY_TRANSLATIONS.items():
        # 對在chip內的分類名稱進行替換 (視頻詳情頁)
        pattern = rf'<a href="[^"]*?categories/[^"]*?\.html" class="chip(?:\s+[^"]*?)?">{zh}</a>'
        replacement = lambda m: m.group(0).replace(f'>{zh}</a>', f'>{en}</a>')
        html_content = re.sub(pattern, replacement, html_content)
        
        # 對在側邊欄的分類名稱進行替換
        pattern = rf'<a href="[^"]*?categories/[^"]*?\.html" class="chip chip-category-sidebar">\s*{zh}\s*\(([0-9]+)\)\s*</a>'
        replacement = lambda m: m.group(0).replace(f'>{zh} ({m.group(1)})</a>', f'>{en} ({m.group(1)})</a>')
        html_content = re.sub(pattern, replacement, html_content)
        
        # 首頁和其他頁面的分類名稱替換
        pattern = rf'<a href="[^"]*?categories/[^"]*?\.html" class="chip chip-category">{zh}</a>'
        replacement = lambda m: m.group(0).replace(f'>{zh}</a>', f'>{en}</a>')
        html_content = re.sub(pattern, replacement, html_content)
    
    return html_content

def process_file(file_path):
    """處理單個HTML文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修正網站標題
    content = fix_website_title(content)
    
    # 優化觀影心得段落
    file_path_str = str(file_path)
    if "/videos/" in file_path_str or "\\videos\\" in file_path_str:
        content = optimize_review_paragraphs(content)
    
    # 翻譯英文版頁面中的分類和女優名稱
    if "/en/" in file_path_str or "\\en\\" in file_path_str:
        content = translate_categories_and_actresses(content)
    
    # 寫回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已處理: {file_path}")

def main():
    # 處理dist目錄下的所有HTML文件
    dist_dir = Path("dist")
    html_files = list(dist_dir.glob("**/*.html"))
    
    count = 0
    total = len(html_files)
    
    for file_path in html_files:
        process_file(file_path)
        count += 1
        print(f"進度: {count}/{total}")
    
    print("所有文件處理完成！")

if __name__ == "__main__":
    main() 