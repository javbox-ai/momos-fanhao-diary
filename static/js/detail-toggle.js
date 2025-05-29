// 控制封面顯示/隱藏
document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('toggleCover');
    const coverContainer = document.querySelector('.video-cover');
    
    if (toggleButton && coverContainer) {
        toggleButton.addEventListener('click', function() {
            const isVisible = coverContainer.style.display !== 'none';
            
            if (isVisible) {
                coverContainer.style.display = 'none';
                toggleButton.textContent = document.documentElement.lang === 'cn' ? '點擊顯示封面' : 'Show Cover';
            } else {
                coverContainer.style.display = 'block';
                toggleButton.textContent = document.documentElement.lang === 'cn' ? '點擊隱藏封面' : 'Hide Cover';
            }
        });
    }
}); 