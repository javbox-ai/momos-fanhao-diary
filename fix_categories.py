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

def translate_file(file_path):
    """翻譯英文版頁面中的分類和女優名稱"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用BeautifulSoup解析文件
        soup = BeautifulSoup(content, 'html.parser')
        
        # 找到所有分類標籤
        category_chips = soup.select('a.chip[href*="categories"]')
        
        # 翻譯分類名稱
        for chip in category_chips:
            category_text = chip.get_text(strip=True)
            # 检查是否有数字
            match = re.search(r'(.*?)\s*\((\d+)\)', category_text)
            if match:
                # 有數字的情況
                name, count = match.groups()
                if name in CATEGORY_TRANSLATIONS:
                    chip.string = f"{CATEGORY_TRANSLATIONS[name]} ({count})"
            else:
                # 沒有數字的情況
                if category_text in CATEGORY_TRANSLATIONS:
                    chip.string = CATEGORY_TRANSLATIONS[category_text]
        
        # 寫回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        print(f"已處理: {file_path}")
        return True
    except Exception as e:
        print(f"處理 {file_path} 時出錯: {e}")
        return False

def main():
    # 處理英文版目錄下的所有HTML文件
    en_dir = Path("dist/en")
    if not en_dir.exists():
        print("英文版目錄不存在!")
        return
    
    html_files = list(en_dir.glob("**/*.html"))
    count = 0
    total = len(html_files)
    
    for file_path in html_files:
        success = translate_file(file_path)
        if success:
            count += 1
        print(f"進度: {count}/{total}")
    
    print("所有文件處理完成！")

if __name__ == "__main__":
    main() 