document.addEventListener('DOMContentLoaded', function() {
    // 選擇所有縮略圖連結
    const thumbnailLinks = document.querySelectorAll('.video-card-thumbnail-link');
    
    // 為每個縮略圖添加模糊效果和遮罩
    thumbnailLinks.forEach(function(link) {
        const img = link.querySelector('.video-card-thumbnail');
        if (img) {
            // 添加模糊效果
            img.classList.add('blur-thumb');
            
            // 創建遮罩元素
            const mask = document.createElement('div');
            mask.classList.add('thumb-mask');
            link.appendChild(mask);
            
            // 檢測是否為移動設備
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            
            if (isMobile) {
                // 移動設備：點擊切換模糊狀態
                link.addEventListener('click', function(event) {
                    // 如果是第一次點擊，阻止導航並清除模糊
                    if (!link.classList.contains('unblur')) {
                        event.preventDefault();
                        link.classList.add('unblur');
                        img.classList.remove('blur-thumb');
                    }
                    // 第二次點擊時正常導航
                });
            }
            // 桌面設備依靠 CSS hover 效果處理
        }
    });
}); 