# AV 心得分享網站

這是一個使用 Flask 和 Jinja2 建立的 AV 心得分享網站，並可以生成靜態頁面。

## 本地測試

1.  **安裝依賴:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **設定環境變數:**
    *   `DEEPSEEK_API_KEY`: 您的 DeepSeek API 金鑰。
    *   `DB_HOST`: 資料庫主機 (預設: localhost)
    *   `DB_USER`: 資料庫使用者 (預設: root)
    *   `DB_PASSWORD`: 資料庫密碼
    *   `DB_DATABASE`: 資料庫名稱 (預設: missav_db)
    *   (可選) `DEEPSEEK_API_URL`: DeepSeek API 端點
3.  **啟動 Flask 開發伺服器:**
    ```bash
    python app.py
    ```
    應用程式將在 `http://127.0.0.1:5000/` (或類似位址) 上運行。

## 產生靜態頁面

提供了幾個 Python 腳本來生成不同類型的靜態頁面，這些頁面會儲存在 `output/` 目錄下。

1.  **生成影片詳細頁面 (前 3 筆):**
    ```bash
    python render_static_detail.py
    ```
2.  **生成女優頁面:**
    ```bash
    python render_static_actress.py
    ```
3.  **生成分類頁面:**
    ```bash
    python render_static_category.py
    ```

生成的靜態頁面包含中文 (`_zh.html`) 和英文 (`_en.html`) 版本。

## 部署 (示例：上傳到靜態網站託管)

1.  **生成所有需要的靜態頁面:** 執行上述所有 `render_static_*.py` 腳本。
2.  **準備檔案:**
    *   `output/` 目錄下的所有 HTML 檔案。
    *   `static/` 目錄下的所有 CSS, JS, 圖片等靜態資源。
    *   (可選) 根目錄下的 `index_zh.html` 和 `index_en.html` (如果需要靜態首頁)。
3.  **上傳:** 將這些檔案和目錄結構上傳到您的靜態網站託管服務 (例如 GitHub Pages, Netlify, Vercel, Cloudflare Pages 等)。確保您的託管服務配置正確，能夠處理子目錄中的 HTML 檔案。

**注意:** 靜態頁面生成腳本目前僅處理部分數據 (例如前 3 筆影片)。您可能需要修改這些腳本以生成所有需要的頁面。