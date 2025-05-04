/**
 * 處理搜索提交
 * 這個函數處理所有頁面上的搜索表單提交
 */
function handleSearchSubmit(event) {
    event.preventDefault(); // 防止表單提交
    
    // 獲取搜索輸入值
    const searchInput = document.getElementById('searchInputHeader');
    const query = searchInput.value.trim();
    
    if (query) {
        // 重定向到 AvHub 搜索頁面
        const searchUrl = `https://avhub.pages.dev/search/${encodeURIComponent(query)}`;
        window.open(searchUrl, '_blank', 'noopener,noreferrer');
    }
}

// 當頁面加載完成後，確保所有搜索表單都正確設置
document.addEventListener('DOMContentLoaded', function() {
    // 確保所有搜索表單都使用handleSearchSubmit函數
    const searchForms = document.querySelectorAll('#searchFormHeader');
    searchForms.forEach(form => {
        form.addEventListener('submit', handleSearchSubmit);
    });
});