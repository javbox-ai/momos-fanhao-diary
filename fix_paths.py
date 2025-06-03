import os
import re
from pathlib import Path

def fix_file_paths(file_path, is_index=False, is_subdir=False):
    """
    修復HTML文件中的路徑問題
    is_index: 是否是根目錄下的index.html
    is_subdir: 是否在子目錄中
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 修正網站標題和META標籤
    content = re.sub(r'<title>(.*?)Fanhao Diary(.*?)</title>', r'<title>\1MOMO Fanhao Diary - 女大生觀影日記\2</title>', content)
    content = re.sub(r'content="(.*?)Fanhao Diary(.*?)"', r'content="\1MOMO Fanhao Diary\2"', content)
    
    # 修正LOGO文字（確保沒有重複的MOMO）
    content = re.sub(r'<a href="[^"]*?" class="logo-text">MOMO MOMO Fanhao Diary</a>', r'<a href="index.html" class="logo-text">MOMO Fanhao Diary</a>', content)
    content = re.sub(r'<a href="[^"]*?" class="logo-text">Fanhao Diary</a>', r'<a href="index.html" class="logo-text">MOMO Fanhao Diary</a>', content)
    
    # 修正Footer
    content = re.sub(r'<p>&copy; 2025 MOMO MOMO Fanhao Diary', r'<p>&copy; 2025 MOMO Fanhao Diary', content)
    content = re.sub(r'<p>MOMO Fanhao Diary &copy; 2025</p>', r'<p>&copy; 2025 MOMO Fanhao Diary - 用心看片，隨手筆記。</p>', content)
    
    # 修復免責聲明和Footer順序
    if "</footer>" in content and '<section class="container disclaimer-section-above-footer card">' in content:
        # 確保免責聲明在Footer前面
        if content.find("</footer>") < content.find('<section class="container disclaimer-section-above-footer card">'):
            # 提取Footer和免責聲明區塊
            footer_match = re.search(r'<footer class="site-footer dark-footer">.*?</footer>', content, re.DOTALL)
            disclaimer_match = re.search(r'<section class="container disclaimer-section-above-footer card">.*?</section>', content, re.DOTALL)
            
            if footer_match and disclaimer_match:
                footer = footer_match.group(0)
                disclaimer = disclaimer_match.group(0)
                
                # 刪除原始區塊
                content = content.replace(footer, "")
                content = content.replace(disclaimer, "")
                
                # 在正確位置插入區塊
                body_end_pos = content.rfind("</body>")
                content = content[:body_end_pos] + disclaimer + "\n\n" + footer + "\n" + content[body_end_pos:]
    
    # 修復絕對路徑
    if is_index:
        # 首頁不需要修改相對路徑，只需要確保沒有以/開頭的絕對路徑
        content = re.sub(r'href="/index([^"]*\.html)"', r'href="index\1.html"', content)
        content = re.sub(r'href="/([^"]*\.html)"', r'href="\1"', content)
        content = re.sub(r'src="/static/([^"]*)"', r'src="static/\1"', content)
    elif is_subdir:
        # 子目錄頁面需要添加相對路徑前綴
        prefix = "../" 
        # 修復CSS和靜態資源路徑
        content = re.sub(r'href="/static/([^"]*)"', f'href="{prefix}static/\\1"', content)
        content = re.sub(r'src="/static/([^"]*)"', f'src="{prefix}static/\\1"', content)
        
        # 修復返回首頁的鏈接
        content = re.sub(r'href="/index.html"', f'href="{prefix}index.html"', content)
        
        # 修復其他頁面鏈接
        content = re.sub(r'href="/videos/([^"]*)"', r'href="\1"', content)  # 同級目錄鏈接
        content = re.sub(r'href="/actresses/([^"]*)"', f'href="{prefix}actresses/\\1"', content)
        content = re.sub(r'href="/categories/([^"]*)"', f'href="{prefix}categories/\\1"', content)
        content = re.sub(r'href="/en/([^"]*)"', f'href="{prefix}en/\\1"', content)
        
        # 處理其他絕對路徑
        content = re.sub(r'href="/([^"]*)"', f'href="{prefix}\\1"', content)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"已修復: {file_path}")

def process_directory(directory):
    """遍歷目錄並修復所有HTML文件"""
    dist_path = Path(directory)
    
    # 處理根目錄的HTML文件
    for html_file in dist_path.glob("*.html"):
        is_index = html_file.name.startswith("index")
        fix_file_paths(html_file, is_index=is_index, is_subdir=False)
    
    # 處理子目錄
    for subdir in dist_path.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            print(f"處理子目錄: {subdir.name}")
            for html_file in subdir.glob("*.html"):
                fix_file_paths(html_file, is_index=False, is_subdir=True)

if __name__ == "__main__":
    # 從dist目錄開始處理
    process_directory("dist")
    print("所有路徑已修復完成!") 