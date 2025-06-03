import os
import re
import glob
from bs4 import BeautifulSoup
from pathlib import Path

# 常見女優名稱翻譯字典
ACTRESS_TRANSLATIONS = {
    "波多野結衣": "Yui Hatano",
    "吉澤明步": "Akiho Yoshizawa",
    "麻美由真": "Yuma Asami",
    "風間由美": "Yumi Kazama",
    "初音實": "Minori Hatsune",
    "蕾": "Rei Aoki",
    "篠田優": "Yu Shinoda",
    "小川阿佐美": "Asami Ogawa",
    "天海翼": "Tsubasa Amami",
    "希崎潔西卡": "Jessica Kizaki",
    "霞理沙": "Risa Kasumi",
    "冬月楓": "Kaede Fuyutsuki",
    "穗花": "Honoka",
    "澤村麗子": "Reiko Sawamura",
    "希島愛里": "Airi Kijima",
    "樱心美": "Kokomi Sakura",
    "希志愛野": "Aino Kishi",
    "AIKA": "AIKA",
    "奧田咲": "Saki Okuda",
    "JULIA": "JULIA"
}

def translate_actress_names(file_path):
    """翻譯英文版頁面中的女優名稱"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用BeautifulSoup解析文件
        soup = BeautifulSoup(content, 'html.parser')
        
        # 找到所有女優標籤
        actress_chips = soup.select('a.chip[href*="actresses"]')
        
        # 翻譯女優名稱
        for chip in actress_chips:
            actress_text = chip.get_text(strip=True)
            # 檢查是否有數字
            match = re.search(r'(.*?)\s*\((\d+)\)', actress_text)
            if match:
                # 有數字的情況
                name, count = match.groups()
                if name in ACTRESS_TRANSLATIONS:
                    chip.string = f"{ACTRESS_TRANSLATIONS[name]} ({count})"
            else:
                # 沒有數字的情況
                if actress_text in ACTRESS_TRANSLATIONS:
                    chip.string = ACTRESS_TRANSLATIONS[actress_text]
        
        # 修改英文版頁面的頁面標題中的女優名稱
        video_titles = soup.select('.video-card-title a')
        for title in video_titles:
            title_text = title.get_text()
            # 在標題的末尾查找女優名稱
            for jp_name, en_name in ACTRESS_TRANSLATIONS.items():
                if title_text.endswith(f"- {jp_name}"):
                    new_title = title_text.replace(f"- {jp_name}", f"- {en_name}")
                    title.string = new_title
        
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
        success = translate_actress_names(file_path)
        if success:
            count += 1
        print(f"進度: {count}/{total}")
    
    print("所有文件處理完成！")

if __name__ == "__main__":
    main() 