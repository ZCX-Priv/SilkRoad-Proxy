/**
 * 同页面链接转换器
 * 将所有新标签页打开的链接改为在同一页面打开
 */

(function() {
    // 主函数：处理所有链接
    function convertAllLinks() {
        // 获取页面上所有链接
        const links = document.querySelectorAll('a[target="_blank"]');
        
        // 遍历所有链接并修改其target属性
        links.forEach(link => {
            link.setAttribute('target', '_self');
            
            // 可选：添加视觉指示器，表明链接已被修改
            link.style.borderBottom = '1px dotted #0066cc';
            
            // 添加自定义数据属性，标记已处理过的链接
            link.dataset.convertedLink = 'true';
        });
        
        console.log(`已将${links.length}个新标签页链接转换为同页面打开`);
    }
    
    // 初始转换现有链接
    convertAllLinks();
    
    // 监听DOM变化，处理动态加载的内容
    const observer = new MutationObserver(mutations => {
        let hasNewLinks = false;
        
        // 检查是否有新链接被添加
        mutations.forEach(mutation => {
            if (mutation.addedNodes.length) {
                hasNewLinks = true;
            }
        });
        
        // 如果有新链接，重新运行转换
        if (hasNewLinks) {
            convertAllLinks();
        }
    });
    
    // 配置观察器
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // 返回公共API
    return {
        convertLinks: convertAllLinks,
        stopObserving: () => observer.disconnect()
    };
})();