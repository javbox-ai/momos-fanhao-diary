/**
 * 處理搜索提交
 * 這個函數處理所有頁面上的搜索表單提交
 */
function handleSearchSubmit(event) {
    event.preventDefault();
    
    // 獲取搜索輸入值
    const searchInput = document.getElementById('searchInputHeader');
    const query = searchInput.value.trim();
    
    if (!query) return; // 如果搜索為空，不執行任何操作
    
    // 獲取當前語言
    const currentLang = document.documentElement.lang || 'zh';
    
    // 構建搜索URL - 返回到根目錄的搜索頁面
    let searchPath = '';
    
    // 檢測當前頁面的深度
    const pathSegments = window.location.pathname.split('/');
    if (pathSegments.length > 2 && pathSegments[pathSegments.length-2] !== '') {
        // 如果在子目錄中（如 videos/ 或 categories/），則需要回到根目錄
        searchPath = '../../';
    }
    
    // 重定向到搜索結果頁面
    window.location.href = `${searchPath}index_${currentLang}.html?q=${encodeURIComponent(query)}`;
}

// 當頁面加載完成後，確保所有搜索表單都正確設置
document.addEventListener('DOMContentLoaded', function() {
    // 確保所有搜索表單都使用handleSearchSubmit函數
    const searchForms = document.querySelectorAll('#searchFormHeader');
    searchForms.forEach(form => {
        form.addEventListener('submit', handleSearchSubmit);
    });
});