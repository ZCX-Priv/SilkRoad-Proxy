# SilkRoad-Proxy

SilkRoad-Proxy是一个功能强大的HTTP/HTTPS代理服务器，提供网页访问、用户认证和缓存管理等功能。

## 功能特点

- 支持HTTP/HTTPS代理
- 用户认证系统
- 会话管理
- 客户端缓存控制
- 链接自动修正
- 自定义错误页面

## 系统要求

- Python 3.6+
- 依赖库：httpx==0.28.1, loguru==0.7.3, publicsuffix2==2.20191221

## 安装指南

1. 克隆仓库到本地

```bash
git clone https://github.com/yourusername/SilkRoad-Proxy.git
cd SilkRoad-Proxy
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

配置文件位于 `databases/config.json`，可以根据需要修改以下参数：

- `CERT_FILE`/`KEY_FILE`: SSL证书和密钥文件路径
- `FAVICON_FILE`: 网站图标文件路径
- `INDEX_FILE`/`LOGIN_FILE`: 主页和登录页模板文件路径
- `CHAT_FILE`: 聊天页面模板文件路径
- `FORBIDDEN_FILE`/`NOT_FOUND_FILE`: 403禁止访问和404页面未找到模板文件路径
- `LOG_FILE`: 日志文件路径
- `LOGIN_PATH`: 登录页面路径
- `FAVICON_PATH`: 网站图标路径
- `CACHE_ENABLED`: 是否启用缓存
- `CACHE_HTML`/`CACHE_MEDIA`/`CACHE_OTHER`: HTML、媒体和其他文件的缓存设置
- `CACHE_LARGE_FILES`: 是否缓存大文件
- `SERVER_NAME`: 服务器名称
- `SESSION_COOKIE_NAME`: 会话Cookie名称
- `SCHEME`: 协议（http/https）
- `DOMAIN`: 域名
- `BIND_IP`: 绑定IP地址
- `PORT`: 端口号
- `SERVER`: 服务器URL

## 用户管理

用户信息存储在 `databases/users.json` 文件中，格式为：

```json
{
    "username1": "password1",
    "username2": "password2"
}
```

## 黑名单管理

网站黑名单配置在 `databases/blacklist.json` 文件中。

## 使用方法

1. 启动代理服务器

```bash
python SilkRoad.py
```

2. 在浏览器中访问配置的地址和端口（默认为 http://127.0.0.1:8080）

3. 使用配置的用户名和密码登录

4. 通过代理访问网站，格式为：`http://127.0.0.1:8080/http://example.com`

## 开机自启

- 使用 `添加开机自启.bat` 将程序添加到Windows开机启动项
- 使用 `解除开机自启.bat` 移除开机启动项

## 安全说明

- 默认SSL证书仅用于开发测试，生产环境请替换为有效的SSL证书
- 请妥善保管用户凭据信息
- 建议在生产环境中修改默认端口和凭据

## 项目结构

```
SilkRoad-Proxy/
├── LICENSE
├── Readme.md
├── SilkRoad.py          # 主程序
├── SilkRoad.log         # 日志文件
├── databases/           # 数据文件目录
│   ├── blacklist.json   # 黑名单配置
│   ├── config.json      # 系统配置
│   └── users.json       # 用户数据
├── ssl/                 # SSL证书目录
│   ├── cert.pem         # 证书文件
│   └── key.pem          # 密钥文件
├── static/              # 静态资源目录
│   ├── css/             # CSS样式文件
│   │   ├── all.min.css
│   │   ├── animation.css
│   │   ├── error.css
│   │   ├── font.css
│   │   ├── github.min.css
│   │   ├── iconfont.css
│   │   ├── iziToast.min.css
│   │   ├── katex.min.css
│   │   ├── loading.css
│   │   ├── mobile.css
│   │   └── style.css
│   ├── font/            # 字体文件
│   │   ├── MiSans-Regular.subset.ttf
│   │   ├── MiSans-Regular.subset.woff2
│   │   ├── MiSans-Regular.woff2
│   │   ├── iconfont-exp.eot
│   │   ├── iconfont-exp.svg
│   │   ├── iconfont-exp.ttf
│   │   ├── iconfont-exp.woff
│   │   ├── iconfont-exp.woff2
│   │   ├── iconfont.ttf
│   │   ├── iconfont.woff
│   │   └── iconfont.woff2
│   ├── img/             # 图片资源
│   │   ├── background1.webp
│   │   ├── background10.webp
│   │   ├── background11.webp
│   │   ├── background2.webp
│   │   ├── background3.webp
│   │   ├── background4.webp
│   │   ├── background5.webp
│   │   ├── background6.webp
│   │   ├── background7.webp
│   │   ├── background8.webp
│   │   ├── background9.webp
│   │   └── bgimg.jpg
│   └── js/              # JavaScript文件
│       ├── auto-render.min.js
│       ├── bash.min.js
│       ├── core.min.js
│       ├── cpp.min.js
│       ├── iziToast.min.js
│       ├── java.min.js
│       ├── javascript.min.js
│       ├── jquery.min.js
│       ├── js.cookie.js
│       ├── katex.min.js
│       ├── main.js
│       ├── marked.min.js
│       ├── python.min.js
│       └── set.js
├── temp/                # 临时文件目录
│   ├── html/
│   ├── media/
│   └── responses/
├── templates/           # 页面模板目录
│   ├── 403.html         # 禁止访问页面
│   ├── 404.html         # 页面未找到
│   ├── chat.html        # 聊天页面
│   ├── index.html       # 主页
│   └── login.html       # 登录页
├── favicon.ico          # 网站图标
├── requirements.txt     # 依赖库列表
├── 添加开机自启.bat      # 添加开机自启脚本
└── 解除开机自启.bat      # 解除开机自启脚本
```

## 许可证

请查看项目中的 LICENSE 文件了解许可证信息。

## 贡献指南

欢迎提交问题报告和功能建议，也欢迎通过Pull Request贡献代码。