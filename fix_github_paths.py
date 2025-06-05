import os
import re
from pathlib import Path

def fix_file_paths_for_github(file_path):
    """
    修復HTML文件中的路徑問題，專門針對GitHub Pages環境
    將所有靜態資源路徑改為絕對路徑（以/開頭）
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 將相對路徑的CSS和靜態資源改為絕對路徑
    # 修改CSS路徑
    content = re.sub(r'href="(?:\.\./)*static/([^"]*?)"', r'href="/static/\1"', content)
    
    # 修改圖片和其他靜態資源路徑
    content = re.sub(r'src="(?:\.\./)*static/([^"]*?)"', r'src="/static/\1"', content)
    
    # 修改favicon路徑
    content = re.sub(r'href="(?:\.\./)*static/favicon.png"', r'href="/static/favicon.png"', content)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"已修復GitHub路徑: {file_path}")

def process_directory(directory):
    """遍歷目錄並修復所有HTML文件"""
    dist_path = Path(directory)
    
    # 處理根目錄的HTML文件
    for html_file in dist_path.glob("*.html"):
        fix_file_paths_for_github(html_file)
    
    # 處理子目錄
    for subdir in dist_path.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            print(f"處理子目錄: {subdir.name}")
            for html_file in subdir.glob("**/*.html"):
                fix_file_paths_for_github(html_file)

if __name__ == "__main__":
    # 從dist目錄開始處理
    process_directory("dist")
    print("所有GitHub Pages路徑已修復完成!")