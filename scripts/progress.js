// SilkRoad自定义脚本 - 页面加载进度条
(function() {
    console.log('SilkRoad自定义脚本已加载 - 页面加载进度条');
    
    // 在页面开始加载时立即执行
    let startTime = Date.now();
    let progressBar, progressContainer;
    let loadingComplete = false;
    let fadeOutTimeout;
    
    // 创建进度条样式
    function createStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .silkroad-progress-container {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background-color: rgba(0, 0, 0, 0.1);
                z-index: 10000;
                pointer-events: none;
                transition: opacity 0.5s ease;
            }
            
            .silkroad-progress-bar {
                height: 100%;
                width: 0%;
                background: linear-gradient(to right, #4cd964, #5ac8fa, #007aff, #34aadc, #5856d6, #ff2d55);
                background-size: 500% 100%;
                animation: silkroad-progress-animation 2s ease infinite;
                transition: width 0.3s ease;
                border-radius: 0 2px 2px 0;
                box-shadow: 0 0 10px rgba(0, 120, 255, 0.5);
            }
            
            @keyframes silkroad-progress-animation {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // 创建进度条DOM元素
    function createProgressBar() {
        progressContainer = document.createElement('div');
        progressContainer.className = 'silkroad-progress-container';
        
        progressBar = document.createElement('div');
        progressBar.className = 'silkroad-progress-bar';
        
        progressContainer.appendChild(progressBar);
        document.body.appendChild(progressContainer);
    }
    
    // 更新进度条
    function updateProgress(percent) {
        if (!progressBar || loadingComplete) return;
        
        // 确保进度条平滑增长且不会后退
        const currentWidth = parseFloat(progressBar.style.width) || 0;
        if (percent > currentWidth) {
            progressBar.style.width = percent + '%';
        }
        
        // 当进度接近100%时，减缓增长速度
        if (percent >= 90 && !loadingComplete) {
            const remainingProgress = 100 - percent;
            const slowIncrement = remainingProgress * 0.1;
            
            setTimeout(() => {
                updateProgress(percent + slowIncrement);
            }, 200);
        }
    }
    
    // 完成加载
    function completeProgress() {
        if (loadingComplete || !progressBar) return;
        
        loadingComplete = true;
        progressBar.style.width = '100%';
        
        // 延迟后淡出进度条
        clearTimeout(fadeOutTimeout);
        fadeOutTimeout = setTimeout(() => {
            progressContainer.style.opacity = '0';
            setTimeout(() => {
                if (progressContainer && progressContainer.parentNode) {
                    progressContainer.parentNode.removeChild(progressContainer);
                }
            }, 500);
        }, 300);
    }
    
    // 模拟进度增长
    function simulateProgress() {
        const maxSimulatedProgress = 90; // 最大模拟进度
        const loadTime = 10000; // 假设页面加载时间上限为10秒
        const elapsed = Date.now() - startTime;
        const progress = Math.min(maxSimulatedProgress, (elapsed / loadTime) * 100);
        
        updateProgress(progress);
        
        if (progress < maxSimulatedProgress && !loadingComplete) {
            requestAnimationFrame(simulateProgress);
        }
    }
    
    // 初始化
    function init() {
        // 如果DOM已经加载，立即创建进度条
        if (document.readyState === 'loading') {
            createStyles();
            document.addEventListener('DOMContentLoaded', () => {
                createProgressBar();
                simulateProgress();
            });
        } else {
            createStyles();
            createProgressBar();
            simulateProgress();
        }
        
        // 监听页面加载完成事件
        window.addEventListener('load', () => {
            completeProgress();
        });
        
        // 如果页面加载时间过长，确保进度条最终会完成
        setTimeout(() => {
            completeProgress();
        }, 15000);
    }
    
    // 启动进度条
    init();
})();