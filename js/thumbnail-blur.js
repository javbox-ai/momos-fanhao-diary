document.addEventListener('DOMContentLoaded', function() {
    // 選擇所有縮略圖連結和圖片
    const thumbnailLinks = document.querySelectorAll('.video-card-thumbnail-link');
    const thumbnailImages = document.querySelectorAll('.video-card-thumbnail');
    
    // 為所有縮圖添加模糊效果
    thumbnailImages.forEach(function(img) {
        // 添加模糊效果類
        img.classList.add('blur-thumb');
    });
    
    // 為所有縮圖連結添加遮罩
    thumbnailLinks.forEach(function(link) {
        // 檢查是否已經有遮罩元素
        if (!link.querySelector('.thumb-mask')) {
            // 創建遮罩元素
            const mask = document.createElement('div');
            mask.classList.add('thumb-mask');
            link.appendChild(mask);
        }
        
        // 檢測是否為移動設備
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (isMobile) {
            // 移動設備：點擊切換模糊狀態
            link.addEventListener('click', function(event) {
                // 如果是第一次點擊，阻止導航並清除模糊
                if (!link.classList.contains('unblur')) {
                    event.preventDefault();
                    link.classList.add('unblur');
                    const img = link.querySelector('.video-card-thumbnail');
                    if (img) {
                        img.classList.remove('blur-thumb');
                    }
                }
                // 第二次點擊時正常導航
            });
        }
        // 桌面設備依靠 CSS hover 效果處理
    });
    
    console.log('縮圖模糊效果已加載');
}); 