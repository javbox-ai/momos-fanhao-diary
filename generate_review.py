#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from openai import OpenAI
import random
import re
from dotenv import load_dotenv

# 加載環境變量
load_dotenv()

# 配置API
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')

# 初始化API客戶端
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)

# 心得生成Prompt
CN_REVIEW_PROMPT = """你是一位 20 出頭的女大學生MOMO，平常會偷偷看片，並寫下觀影筆記當作深夜小日記。
請幫我撰寫一篇 番號為「{video_code}」的心得筆記，風格要口語、生動、輕鬆、幽默、有少女心，總字數必須控制在400字以內，適合投稿到部落格或心得網站。
請嚴格按照以下四個段落結構撰寫，每段都要有emoji開頭和明顯小標題：

1. 【三行短評】：用emoji開頭，三句話簡潔點評，語氣要活潑俏皮
2. 【今天最愛】：用emoji開頭，描述最喜歡的一個場景或情節，語氣要興奮或害羞
3. 【女大生吐槽】：用emoji開頭，從女生角度吐槽劇情或演員表現的有趣地方
4. 【本片結論】：用emoji開頭，總結感受並給出評分或推薦度

注意事項：
- 使用親暱、口語、非正式語氣（像寫給閨蜜看的那種）
- 嚴格控制在400字以內
- 適度加入貼標籤語（如：#制服控 #主觀視角 #潮吹 #想再看一遍）放在結尾
- 避免過度重複 AI 用詞，務必有段落、句式變化
- 影片標題：'{video_title}'，女優：'{actress_name}'，類型：{keywords}。原始簡介：'{base_description}'
- 從心得中選出一句最精彩、最有爆點的金句，將在網站上作為「今日金句」高亮顯示"""

def generate_content_with_deepseek(prompt_text, video_code="TEST-001"):
    """使用DeepSeek API生成心得內容"""
    print(f"正在為影片 {video_code} 生成心得...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=600,
            temperature=0.7,
        )
        ai_text = response.choices[0].message.content.strip()
        return ai_text
    except Exception as e:
        print(f"生成心得時出錯: {e}")
        return f"AI生成失敗 ({e})"

def extract_highlight_quote(ai_review):
    """从心得中提取一句最精彩的金句"""
    if not ai_review:
        return None
    
    # 尝试从心得文本中提取带有情感和特色的句子作为金句
    sentences = re.split(r'[。！？\.!?]', ai_review)
    sentences = [s.strip() for s in sentences if 10 < len(s.strip()) < 50]  # 过滤太短或太长的句子
    
    if not sentences:
        return None
    
    # 优先选择有感叹号或问号的句子，因为这些句子通常更有情感
    emphasis_sentences = [s for s in sentences if '！' in s or '?' in s or '！' in s or '?' in s]
    if emphasis_sentences:
        return random.choice(emphasis_sentences)
    
    # 如果没有带强调的句子，随机选择一句适当长度的句子
    return random.choice(sentences)

def main():
    # 測試數據
    video_code = "TEST-001"
    video_title = "測試標題：女大生的放學後私生活"
    actress_name = "測試女優"
    keywords = "學生, 制服, 浴室"
    base_description = "這是一部關於女大生放學後私生活的影片，有很多精彩的場景。"
    
    # 填充Prompt模板
    prompt = CN_REVIEW_PROMPT.format(
        video_code=video_code,
        video_title=video_title,
        actress_name=actress_name,
        keywords=keywords,
        base_description=base_description
    )
    
    # 生成心得
    ai_content = generate_content_with_deepseek(prompt, video_code)
    
    # 提取金句
    highlight_quote = extract_highlight_quote(ai_content)
    
    # 輸出結果
    print("\n" + "="*50)
    print(f"影片編號: {video_code}")
    print(f"影片標題: {video_title}")
    print(f"女優: {actress_name}")
    print(f"分類: {keywords}")
    print("="*50)
    
    if highlight_quote:
        print("\n今日金句:")
        print(f"「{highlight_quote}」")
        print("-"*50)
    
    print("\n觀影心得:")
    print(ai_content)
    print("="*50)

if __name__ == "__main__":
    main() 