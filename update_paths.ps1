# 批量修改HTML文件中的相對路徑為絕對路徑
# 此腳本將網站中的相對路徑轉換為絕對路徑，以便在GitHub Pages上正確顯示

# 記錄開始時間
$startTime = Get-Date

# 設置錯誤操作首選項
$ErrorActionPreference = "Continue"

# 定義要處理的目錄
$directories = @(
    "c:\AItools\網站模板\static_site\categories",
    "c:\AItools\網站模板\static_site\actresses",
    "c:\AItools\網站模板\static_site\error"
    # "c:\AItools\網站模板\static_site\videos" # 視頻目錄暫時註釋，因為目前沒有HTML文件
)

# 獲取所有HTML文件
$files = @()
foreach ($dir in $directories) {
    $files += Get-ChildItem -Path "$dir\*.html"
}

# 添加根目錄下的HTML文件
$rootFiles = Get-ChildItem -Path "c:\AItools\網站模板\static_site\*.html"
$files += $rootFiles

# 顯示處理進度
$totalFiles = $files.Count
$currentFile = 0

foreach($file in $files) {
    $currentFile++
    Write-Host "[$currentFile/$totalFiles] Processing $($file.Name)..."
    
    try {
    $content = Get-Content -Path $file.FullName -Raw
    
    # 替換靜態資源路徑
    $content = $content.Replace('../../static/favicon.png', '/momos-fanhao-diary/static/favicon.png')
    $content = $content.Replace('../static/favicon.png', '/momos-fanhao-diary/static/favicon.png')
    $content = $content.Replace('./static/favicon.png', '/momos-fanhao-diary/static/favicon.png')
    $content = $content.Replace('static/favicon.png', '/momos-fanhao-diary/static/favicon.png')
    
    $content = $content.Replace('../../static/style.css', '/momos-fanhao-diary/static/style.css')
    $content = $content.Replace('../static/style.css', '/momos-fanhao-diary/static/style.css')
    $content = $content.Replace('./static/style.css', '/momos-fanhao-diary/static/style.css')
    $content = $content.Replace('static/style.css', '/momos-fanhao-diary/static/style.css')
    
    $content = $content.Replace('../../static/LOGO.png', '/momos-fanhao-diary/static/LOGO.png')
    $content = $content.Replace('../static/LOGO.png', '/momos-fanhao-diary/static/LOGO.png')
    $content = $content.Replace('./static/LOGO.png', '/momos-fanhao-diary/static/LOGO.png')
    $content = $content.Replace('static/LOGO.png', '/momos-fanhao-diary/static/LOGO.png')
    
    # 替換首頁連結
    $content = $content.Replace('../../index_zh.html', '/momos-fanhao-diary/index.html')
    $content = $content.Replace('../index_zh.html', '/momos-fanhao-diary/index.html')
    $content = $content.Replace('../../index_en.html', '/momos-fanhao-diary/index_en.html')
    $content = $content.Replace('../index_en.html', '/momos-fanhao-diary/index_en.html')
    
    # 替換視頻頁面連結
    $content = $content.Replace('../../videos/', '/momos-fanhao-diary/videos/')
    $content = $content.Replace('../videos/', '/momos-fanhao-diary/videos/')
    $content = $content.Replace('./videos/', '/momos-fanhao-diary/videos/')
    $content = $content.Replace('videos/', '/momos-fanhao-diary/videos/')
    
    # 替換女優頁面連結
    $content = $content.Replace('../../actresses/', '/momos-fanhao-diary/actresses/')
    $content = $content.Replace('../actresses/', '/momos-fanhao-diary/actresses/')
    $content = $content.Replace('./actresses/', '/momos-fanhao-diary/actresses/')
    $content = $content.Replace('actresses/', '/momos-fanhao-diary/actresses/')
    
    # 替換分類頁面連結
    $content = $content.Replace('../../categories/', '/momos-fanhao-diary/categories/')
    $content = $content.Replace('../categories/', '/momos-fanhao-diary/categories/')
    $content = $content.Replace('./categories/', '/momos-fanhao-diary/categories/')
    $content = $content.Replace('categories/', '/momos-fanhao-diary/categories/')
    
    # 添加路徑解析器腳本（如果尚未添加）
    if(!($content.Contains('path-resolver.js'))) {
        $scriptTag = '    <script src="/momos-fanhao-diary/static/path-resolver.js"></script> <!-- 添加路徑解析器腳本 -->'
        $content = $content.Replace('</head>', "$scriptTag`r`n</head>")
    }
    
    # 保存修改後的內容
    Set-Content -Path $file.FullName -Value $content -NoNewline
    }
    catch {
        Write-Host "錯誤: 處理文件 $($file.Name) 時發生問題: $_" -ForegroundColor Red
    }
}

# 計算執行時間
$endTime = Get-Date
$executionTime = ($endTime - $startTime).TotalSeconds

# 顯示執行摘要
Write-Host "-----------------------------------------" -ForegroundColor Green
Write-Host "執行摘要:" -ForegroundColor Green
Write-Host "總共處理文件數: $($files.Count)" -ForegroundColor Green
Write-Host "執行時間: $([math]::Round($executionTime, 2)) 秒" -ForegroundColor Green
Write-Host "所有文件已成功更新!" -ForegroundColor Green
Write-Host "-----------------------------------------" -ForegroundColor Green