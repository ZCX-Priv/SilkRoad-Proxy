// 在页面加载完成后执行
window.addEventListener('load', function () {
    //载入动画
    $('#loading-box').attr('class', 'loaded');
    $('#bg').css("cssText", "transform: scale(1);filter: blur(0px);transition: ease 1.5s;");
    $('#section').css("cssText", "opacity: 1;transition: ease 1.5s;");
    $('.cover').css("cssText", "opacity: 1;transition: ease 1.5s;");

    //用户欢迎
    iziToast.settings({
        timeout: 3000,
        backgroundColor: 'rgba(255, 255, 255, 0.25)',  // 改为rgba格式提高兼容性
        titleColor: '#efefef',
        messageColor: '#efefef',
        progressBar: false,
        close: false,
        closeOnEscape: true,
        position: 'topCenter',
        transitionIn: 'bounceInDown',
        transitionOut: 'flipOutX',
        displayMode: 'replace',
        layout: '1'
    });
    setTimeout(function () {
        iziToast.show({
            title: hello,
            message: '欢迎来到 丝绸之路'
        });
    }, 800);

    //中文字体缓加载-此处写入字体源文件
    //先行加载简体中文子集，后续补全字集
    //由于压缩过后的中文字体仍旧过大，可转移至对象存储或 CDN 加载
    if ('FontFace' in window) {  // 添加FontFace API检测
        try {
            var font = new FontFace(
                "MiSans",
                "url(" + "./static/font/MiSans-Regular.woff2" + ")"
            );
            document.fonts.add(font);
            font.load().catch(function(err) {
                console.log('字体加载失败:', err);
            });
        } catch (e) {
            console.log('字体API不支持:', e);
        }
    }

    // 检测浏览器是否支持backdrop-filter
    var testEl = document.createElement('div');
    var isBackdropFilterSupported = ('backdropFilter' in testEl.style) || ('webkitBackdropFilter' in testEl.style);
    
    // 检查Chrome版本
    var isOldChrome = false;
    var chromeMatch = navigator.userAgent.match(/Chrome\/([0-9]+)/);
    if (chromeMatch && parseInt(chromeMatch[1]) <= 76) {
        isOldChrome = true;
    }
    
    // 如果不支持backdrop-filter或是旧版Chrome，添加类名到body
    if (!isBackdropFilterSupported || isOldChrome) {
        document.body.classList.add('no-backdrop-filter');
    }
    
    // 确保搜索框正常工作
    if (document.querySelector('.sou-button') && document.querySelector('.wd') && document.querySelector('#search-submit')) {
        // 搜索框元素存在，确保事件绑定
        document.querySelector('.sou-button').addEventListener('click', function() {
            if (document.querySelector('.wd').value !== '') {
                document.querySelector('#search-submit').click();
            }
        });
    }
}, false);

//进入问候
var now = new Date(), hour = now.getHours();  // 添加var关键字
var hello;  // 提前声明hello变量
if (hour < 6) {
    hello = "凌晨好";
} else if (hour < 9) {
    hello = "早上好";
} else if (hour < 12) {
    hello = "上午好";
} else if (hour < 14) {
    hello = "中午好";
} else if (hour < 17) {
    hello = "下午好";
} else if (hour < 19) {
    hello = "傍晚好";
} else if (hour < 22) {
    hello = "晚上好";
} else {
    hello = "夜深了";
}

//获取时间
var t = null;
t = setTimeout(time, 1000);

function time() {
    clearTimeout(t);
    var dt = new Date();  // 添加var关键字
    var mm = dt.getMonth() + 1;
    var d = dt.getDate();
    var weekday = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    var day = dt.getDay();
    var h = dt.getHours();
    var m = dt.getMinutes();
    if (h < 10) {
        h = "0" + h;
    }
    if (m < 10) {
        m = "0" + m;
    }
    if ($("#time_text").length) {  // 添加元素存在检查
        $("#time_text").html(h + '<span id="point">:</span>' + m);
    }
    if ($("#day").length) {  // 添加元素存在检查
        $("#day").html(mm + "&nbsp;月&nbsp;" + d + "&nbsp;日&nbsp;" + weekday[day]);
    }
    t = setTimeout(time, 1000);
}

//Tab书签页
$(function () {
    $(".mark .tab .tab-item").click(function () {
        $(this).addClass("active").siblings().removeClass("active");
        $(".products .mainCont").eq($(this).index()).css("display", "flex").siblings().css("display", "none");
    });
});

//设置
$(function () {
    $(".set .tabs .tab-items").click(function () {
        $(this).addClass("actives").siblings().removeClass("actives");
        $(".productss .mainConts").eq($(this).index()).css("display", "flex").siblings().css("display", "none");
    });
});

//输入框为空时阻止跳转
$(window).keydown(function (e) {
    var key = window.event ? e.keyCode : e.which;
    if (key.toString() == "13") {
        if ($(".wd").val() == "") {
            return false;
        }
    }
});

//点击搜索按钮
$(".sou-button").click(function () {
    if ($(".wd").length && $("#search-submit").length) {  // 添加元素存在检查
        if ($(".wd").val() != "") {
            $("#search-submit").click();
        }
    }
});

//鼠标中键点击事件
$(window).mousedown(function (event) {
    if (event.button == 1 && $("#time_text").length) {  // 添加元素存在检查
        $("#time_text").click();
    }
});

//控制台输出
var styleTitle1 = 
"font-size: 20px;" +
"font-weight: 600;" +
"color: rgb(244,167,89);";

var styleTitle2 = 
"font-size:12px;" +
"color: rgb(244,167,89);";

var styleContent = 
"color: rgb(30,152,255);";

var title1 = '丝绸之路';
var title2 = 'Nav';
var content = '版 本 号：3.0';

try {
    console.log("%c" + title1 + " %c" + title2 + "\n%c" + content, styleTitle1, styleTitle2, styleContent);
} catch (e) {
    console.log("丝绸之路 Nav - 版本号：3.0");
}
