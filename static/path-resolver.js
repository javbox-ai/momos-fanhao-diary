/**
 * path-resolver.js
 * 這個腳本用於自動檢測當前頁面的URL路徑深度，並動態調整CSS和其他靜態資源的路徑
 * 這樣無論是在本地環境還是GitHub Pages上，網站都能正確載入樣式
 */

document.addEventListener('DOMContentLoaded', function() {
    // 獲取當前頁面的路徑
    const currentPath = window.location.pathname;
    
    // 檢測是否在GitHub Pages上運行
    const isGitHubPages = window.location.hostname.includes('github.io');
    
    // 獲取當前頁面的目錄深度
    let pathDepth = 0;
    if (currentPath !== '/' && currentPath !== '/index.html') {
        // 計算路徑中的目錄層級數
        // 例如：/actresses/初川南_zh.html 的深度為 1
        pathDepth = currentPath.split('/').filter(Boolean).length - 1;
        
        // 如果是文件而不是目錄，減去1
        if (!currentPath.endsWith('/')) {
            const lastSegment = currentPath.split('/').pop();
            if (lastSegment && lastSegment.includes('.')) {
                // 不需要減1，因為我們已經計算了目錄深度
            }
        }
    }
    
    // 根據深度生成相對路徑前綴
    let pathPrefix = '';
    for (let i = 0; i < pathDepth; i++) {
        pathPrefix += '../';
    }
    
    // 如果是在GitHub Pages上，並且沒有自定義域名，可能需要添加倉庫名
    if (isGitHubPages) {
        // 從hostname中提取用戶名和倉庫名
        const parts = window.location.hostname.split('.');
        if (parts[0] && parts[1] === 'github' && parts[2] === 'io') {
            const username = parts[0];
            // 從pathname中提取倉庫名（如果有）
            const repoName = window.location.pathname.split('/')[1];
            if (repoName && repoName !== '') {
                // 如果已經包含倉庫名在路徑中，則不需要額外處理
            }
        }
    }
    
    // 更新所有CSS鏈接
    updateResourcePaths('link[rel="stylesheet"]', 'href', pathPrefix);
    
    // 更新所有圖片鏈接
    updateResourcePaths('img', 'src', pathPrefix);
    
    // 更新所有腳本鏈接
    updateResourcePaths('script', 'src', pathPrefix);
    
    // 更新所有圖標鏈接
    updateResourcePaths('link[rel="icon"]', 'href', pathPrefix);
    
    // 更新所有超鏈接（不僅限於以static開頭的相對路徑）
    updateResourcePaths('a:not([href^="http"]):not([href^="#"]):not([href^="mailto:"])', 'href', pathPrefix);
    
    // 更新所有表單動作（僅限於以static開頭的相對路徑）
    updateResourcePaths('form[action^="static/"]', 'action', pathPrefix);
    
    // 更新所有視頻源
    updateResourcePaths('video source', 'src', pathPrefix);
    
    // 更新所有音頻源
    updateResourcePaths('audio source', 'src', pathPrefix);
    
    // 更新所有iframe源
    updateResourcePaths('iframe', 'src', pathPrefix);
    
    // 更新所有object數據
    updateResourcePaths('object', 'data', pathPrefix);
    
    // 更新所有embed源
    updateResourcePaths('embed', 'src', pathPrefix);
    
    // 更新所有track源
    updateResourcePaths('track', 'src', pathPrefix);
    
    // 更新所有input源（例如圖像按鈕）
    updateResourcePaths('input[type="image"]', 'src', pathPrefix);
    
    // 更新所有背景圖片（內聯樣式）
    updateBackgroundImages(pathPrefix);
    
    console.log('Path resolver: 已調整資源路徑，深度為 ' + pathDepth + '，前綴為 "' + pathPrefix + '"');
});

/**
 * 更新指定選擇器元素的資源路徑
 * @param {string} selector - CSS選擇器
 * @param {string} attribute - 要更新的屬性名稱
 * @param {string} pathPrefix - 路徑前綴
 */
function updateResourcePaths(selector, attribute, pathPrefix) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(function(element) {
        const originalPath = element.getAttribute(attribute);
        if (!originalPath || originalPath.startsWith('http') || originalPath.startsWith('//') || originalPath.startsWith('#') || originalPath.startsWith('mailto:')) {
            return;
        }
        
        // 處理以/開頭的路徑（絕對路徑）
        if (originalPath.startsWith('/')) {
            // 對於GitHub Pages，保留以/momos-fanhao-diary開頭的路徑
            if (originalPath.startsWith('/momos-fanhao-diary/')) {
                return;
            }
            // 移除開頭的/，然後添加前綴
            const newPath = pathPrefix + originalPath.substring(1);
            element.setAttribute(attribute, newPath);
        }
        // 處理相對路徑
        else if (!originalPath.startsWith('./') && !originalPath.startsWith('../')) {
            // 如果路徑不是以./或../開頭，添加前綴
            const newPath = pathPrefix + originalPath;
            element.setAttribute(attribute, newPath);
        }
    });
}

/**
 * 更新元素的背景圖片路徑（內聯樣式）
 * @param {string} pathPrefix - 路徑前綴
 */
function updateBackgroundImages(pathPrefix) {
    const elements = document.querySelectorAll('[style*="background-image"]');
    elements.forEach(function(element) {
        const style = element.getAttribute('style');
        if (style && style.includes('url(') && style.includes('static/')) {
            // 使用正則表達式匹配背景圖片URL
            const newStyle = style.replace(/url\(['"]?(static\/[^'"\)]+)['"]?\)/g, function(match, p1) {
                return 'url("' + pathPrefix + p1 + '")';
            });
            element.setAttribute('style', newStyle);
        }
    });
}