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
    
    // 更新所有圖片路徑
    updateResourcePaths('img', 'src', pathPrefix);
    
    // 更新所有favicon
    updateResourcePaths('link[rel="icon"]', 'href', pathPrefix);
    
    // 更新所有a標籤中的相對路徑（排除外部鏈接和錨點鏈接）
    updateResourcePaths('a:not([href^="http"]):not([href^="#"]):not([href^="mailto:"])', 'href', pathPrefix);
    
    // 更新所有meta標籤中的og:image和og:url
    updateResourcePaths('meta[property="og:image"]', 'content', pathPrefix);
    updateResourcePaths('meta[property="og:url"]', 'content', pathPrefix);
    
    // 更新canonical鏈接
    updateResourcePaths('link[rel="canonical"]', 'href', pathPrefix);
    
    /**
     * 更新指定元素的資源路徑
     * @param {string} selector - CSS選擇器
     * @param {string} attribute - 要更新的屬性
     * @param {string} prefix - 路徑前綴
     */
    function updateResourcePaths(selector, attribute, prefix) {
        const elements = document.querySelectorAll(selector);
        
        elements.forEach(element => {
            const originalPath = element.getAttribute(attribute);
            
            // 跳過已經是絕對路徑的URL
            if (!originalPath || originalPath.startsWith('http') || originalPath.startsWith('//') || originalPath.startsWith('#')) {
                return;
            }
            
            // 處理以/開頭的路徑（絕對路徑）
            if (originalPath.startsWith('/')) {
                // 移除開頭的/，然後添加前綴
                const newPath = prefix + originalPath.substring(1);
                element.setAttribute(attribute, newPath);
            } 
            // 處理以../開頭的路徑（相對路徑）
            else if (originalPath.startsWith('../')) {
                // 已經是相對路徑，不需要修改
            }
            // 處理不以/或../開頭的路徑（相對於當前目錄的路徑）
            else if (!originalPath.startsWith('./') && !originalPath.startsWith('../')) {
                // 如果路徑不是以./或../開頭，添加前綴
                const newPath = prefix + originalPath;
                element.setAttribute(attribute, newPath);
            }
        });
    }
    
    console.log('Path resolver initialized. Path depth:', pathDepth, 'Path prefix:', pathPrefix);
});