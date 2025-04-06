import ssl
import re
import random
import string
import time
import json
import http.server
import http.client
import datetime  # 添加此行
from http import HTTPStatus
from socketserver import ThreadingMixIn
from urllib import parse
from threading import Timer, Thread
from publicsuffix2 import PublicSuffixList
import httpx
import gc
import atexit
import shutil
import os
import signal
import sys
import platform
from loguru import logger

# ------------------ 配置与数据加载 ------------------
with open('databases/config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

with open('databases/users.json', 'r', encoding='utf-8') as users_file:
    users_data = json.load(users_file)

# 设置 http.client 最大请求头数量，修复 "get more than 100 headers" 错误
http.client._MAXHEADERS = 1000

# ------------------ 系统与资源管理 ------------------
def periodic_gc():
    """定时释放内存，每1分钟执行一次垃圾回收"""
    gc.collect()
    Timer(60, periodic_gc).start()

periodic_gc()

def clear_temp_cache():
    """程序退出时清除 temp 文件夹中的缓存（包括编译后的 .pyc 与网站缓存）"""
    # 确保使用程序所在目录
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    if os.path.exists(temp_dir):
        try:
            # 先关闭所有打开的文件句柄
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # 尝试打开并立即关闭文件,释放文件句柄
                        with open(file_path, 'rb'):
                            pass
                    except:
                        pass
            
            # 等待100ms让系统完全释放文件句柄
            time.sleep(0.1)
            
            # 删除目录树
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 确认目录是否被删除,如果没有则强制删除
            if os.path.exists(temp_dir):
                os.system(f'rd /s /q "{temp_dir}"' if platform.system() == 'Windows' else f'rm -rf "{temp_dir}"')
            
            logger.info("已清除临时缓存目录。")
        except Exception as e:
            logger.error(f"清除缓存目录时出错: {e}")

# 注册清理函数
atexit.register(clear_temp_cache)

# 添加缓存管理类
class CacheManager:
    """管理系统缓存的类"""
    def __init__(self):
        # 使用程序所在目录
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        self.html_cache_dir = os.path.join(self.base_dir, "html")
        self.media_cache_dir = os.path.join(self.base_dir, "media")
        self.response_cache_dir = os.path.join(self.base_dir, "responses")
        self.max_cache_size = 500 * 1024 * 1024  # 500MB
        self.max_cache_age = 24 * 60 * 60  # 24小时
        
        # 确保缓存目录存在
        self._ensure_cache_dirs()
        
        # 启动定期清理任务
        self._schedule_cleanup()
    
    def _ensure_cache_dirs(self):
        """确保所有缓存目录存在"""
        for dir_path in [self.base_dir, self.html_cache_dir, 
                         self.media_cache_dir, self.response_cache_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.debug(f"创建缓存目录: {dir_path}")
    
    def _schedule_cleanup(self):
        """安排定期清理任务"""
        cleanup_interval = 3600  # 每小时清理一次
        Timer(cleanup_interval, self._cleanup_cache).start()
    
    def _cleanup_cache(self):
        """清理过期和过大的缓存"""
        try:
            logger.info("开始清理缓存...")
            now = time.time()
            total_size = 0
            files_info = []
            
            # 收集所有缓存文件信息
            for root, _, files in os.walk(self.base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_stat = os.stat(file_path)
                        file_size = file_stat.st_size
                        file_mtime = file_stat.st_mtime
                        total_size += file_size
                        files_info.append((file_path, file_size, file_mtime))
                    except (FileNotFoundError, PermissionError) as e:
                        logger.warning(f"无法获取文件信息 {file_path}: {e}")
            
            # 删除过期文件
            expired_files = [(path, size) for path, size, mtime in files_info 
                            if now - mtime > self.max_cache_age]
            for path, size in expired_files:
                try:
                    os.remove(path)
                    total_size -= size
                    logger.debug(f"删除过期缓存文件: {path}")
                except (FileNotFoundError, PermissionError) as e:
                    logger.warning(f"无法删除文件 {path}: {e}")
            
            # 如果缓存仍然过大，按最后访问时间排序删除
            if total_size > self.max_cache_size:
                remaining_files = [(path, size, mtime) for path, size, mtime in files_info 
                                if not any(path == exp_path for exp_path, _ in expired_files)]
                remaining_files.sort(key=lambda x: x[2])  # 按修改时间排序
                
                for path, size, _ in remaining_files:
                    if total_size <= self.max_cache_size:
                        break
                    try:
                        os.remove(path)
                        total_size -= size
                        logger.debug(f"删除过大缓存文件: {path}")
                    except (FileNotFoundError, PermissionError) as e:
                        logger.warning(f"无法删除文件 {path}: {e}")
            
            logger.info(f"缓存清理完成，当前缓存大小: {total_size / 1024 / 1024:.2f}MB")
            
            # 重新安排下一次清理
            self._schedule_cleanup()
        except Exception as e:
            logger.error(f"缓存清理过程中出错: {e}")
            # 即使出错也要重新安排清理
            self._schedule_cleanup()
    
    def get_cache_path(self, url, content_type=None):
        """根据URL和内容类型获取缓存路径"""
        # 使用URL的哈希值作为文件名，避免路径过长或包含非法字符
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # 根据内容类型选择缓存目录
        if content_type and "text/html" in content_type:
            cache_dir = self.html_cache_dir
            ext = ".html"
        elif content_type and ("image/" in content_type or "video/" in content_type or "audio/" in content_type):
            cache_dir = self.media_cache_dir
            # 从content_type中提取扩展名
            ext = "." + content_type.split("/")[-1].split(";")[0]
        else:
            cache_dir = self.response_cache_dir
            ext = ".dat"
        
        return os.path.join(cache_dir, url_hash + ext)
    
    def save_to_cache(self, url, content, content_type=None, headers=None):
        """保存响应内容到缓存"""
        try:
            cache_path = self.get_cache_path(url, content_type)
            
            # 保存内容
            with open(cache_path, 'wb') as f:
                f.write(content)
            
            # 如果提供了headers，也保存它们
            if headers:
                headers_path = cache_path + ".headers"
                with open(headers_path, 'w', encoding='utf-8') as f:
                    json.dump(dict(headers), f)
            
            logger.debug(f"已缓存: {url} -> {cache_path}")
            return True
        except Exception as e:
            logger.warning(f"缓存保存失败 {url}: {e}")
            return False
    
    def get_from_cache(self, url, content_type=None):
        """从缓存获取响应内容"""
        try:
            cache_path = self.get_cache_path(url, content_type)
            headers_path = cache_path + ".headers"
            
            # 检查缓存是否存在且未过期
            if not os.path.exists(cache_path):
                return None, None
            
            file_stat = os.stat(cache_path)
            if time.time() - file_stat.st_mtime > self.max_cache_age:
                # 缓存已过期，删除并返回None
                os.remove(cache_path)
                if os.path.exists(headers_path):
                    os.remove(headers_path)
                return None, None
            
            # 读取缓存内容
            with open(cache_path, 'rb') as f:
                content = f.read()
            
            # 读取headers（如果存在）
            headers = None
            if os.path.exists(headers_path):
                with open(headers_path, 'r', encoding='utf-8') as f:
                    headers = json.load(f)
            
            # 更新访问时间
            os.utime(cache_path, None)
            if os.path.exists(headers_path):
                os.utime(headers_path, None)
            
            logger.debug(f"缓存命中: {url}")
            return content, headers
        except Exception as e:
            logger.warning(f"读取缓存失败 {url}: {e}")
            return None, None
    
    def clear_cache(self, url=None, content_type=None):
        """清除特定URL的缓存或所有缓存"""
        if url:
            try:
                cache_path = self.get_cache_path(url, content_type)
                headers_path = cache_path + ".headers"
                
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                if os.path.exists(headers_path):
                    os.remove(headers_path)
                logger.debug(f"已清除缓存: {url}")
            except Exception as e:
                logger.warning(f"清除缓存失败 {url}: {e}")
        else:
            # 清除所有缓存
            clear_temp_cache()
            self._ensure_cache_dirs()
            logger.info("已清除所有缓存")

# 创建缓存管理器实例
cache_manager = CacheManager()

# 添加系统自检和缓存清理函数
def system_check_and_cleanup():
    """系统启动时的自检和缓存清理"""
    logger.info("开始系统自检和缓存清理...")
    
    # 1. 检查必要的目录是否存在，不存在则创建
    required_dirs = ["temp", "databases", "templates"]
    for dir_name in required_dirs:
        dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"创建目录: {dir_path}")
    
    # 2. 清除自身缓存
    # 清除临时文件夹
    clear_temp_cache()
    
    # 清除__pycache__文件夹
    pycache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__pycache__")
    if os.path.exists(pycache_dir):
        shutil.rmtree(pycache_dir)
        logger.info("清除 __pycache__ 目录")
    
    # 3. 检查配置文件完整性
    try:
        required_configs = ["SERVER", "DOMAIN", "PORT", "BIND_IP", "SCHEME", 
                           "LOGIN_PATH", "FAVICON_PATH", "INDEX_FILE", "LOGIN_FILE", 
                           "FAVICON_FILE", "SESSION_COOKIE_NAME", "SERVER_NAME", "LOG_FILE"]
        missing_configs = [cfg for cfg in required_configs if cfg not in config]
        if missing_configs:
            logger.warning(f"配置文件缺少以下项: {', '.join(missing_configs)}")
    except Exception as e:
        logger.error(f"检查配置文件时出错: {e}")
    
    # 4. 初始化缓存目录结构
    cache_manager._ensure_cache_dirs()
    
    logger.info("系统自检和缓存清理完成")


def exit_confirmation():
    """退出程序时弹出确认对话框"""
    # 在Windows系统上使用tkinter创建图形化对话框
    if platform.system() == "Windows":
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # 创建隐藏的根窗口
            root = tk.Tk()
            root.withdraw()
            
            # 显示确认对话框
            result = messagebox.askyesno("退出确认", "是否退出程序？")
            root.destroy()
            return result
        except ImportError:
            # 如果tkinter不可用，回退到控制台输入
            pass
    
    # 非Windows系统或tkinter不可用时使用控制台输入
    print("\n检测到退出信号。是否退出程序？(y/N): ", end='', flush=True)
    response = sys.stdin.readline().strip().lower()
    return response == 'y'

def signal_handler(sig, frame):
    if exit_confirmation():
        logger.info("程序退出，正在清理缓存...")
        # 强制终止所有线程并退出
        os._exit(0)
    else:
        logger.info("继续运行程序。")

# 注册SIGINT信号处理器（Ctrl+C）
signal.signal(signal.SIGINT, signal_handler)

# 在Windows上使用更可靠的方法捕获窗口关闭事件
if platform.system() == "Windows":
    try:
        import ctypes
        
        # Windows API常量
        CTRL_CLOSE_EVENT = 2
        CTRL_C_EVENT = 0
        
        # 定义控制台处理函数类型
        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
        def console_ctrl_handler(ctrl_type):
            # 处理窗口关闭事件
            if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_C_EVENT):
                if exit_confirmation():
                    logger.info("程序退出，正在清理缓存...")
                    # 使用os._exit()强制终止进程
                    os._exit(0)
                else:
                    logger.info("继续运行程序")
                return 1
            return 0
        
        # 设置控制台控制处理器
        if ctypes.windll.kernel32.SetConsoleCtrlHandler(console_ctrl_handler, 1) == 0:
            logger.warning("无法设置控制台控制处理器")
    except (ImportError, AttributeError) as e:
        logger.warning(f"无法注册Windows控制台事件处理器: {e}")
        # 回退到使用SIGBREAK
        try:
            signal.signal(signal.SIGBREAK, signal_handler)
        except AttributeError:
            logger.warning("无法注册SIGBREAK信号处理器")

# ------------------ 会话与用户管理 ------------------
class Sessions(object):
    def __init__(self, length=64, age=604800, recycle_interval=3600):
        self.charset = string.ascii_letters + string.digits
        self.length = length
        self.age = age
        self.recycle_interval = recycle_interval
        self.sessions = list()
        self.recycle_session()

    def generate_new_session(self):
        new_session = ''.join(random.choice(self.charset) for _ in range(self.length))
        self.sessions.append([new_session, time.time()])
        return new_session

    def is_session_exist(self, session):
        for _session in self.sessions:
            if _session[0] == session:
                _session[1] = time.time()
                return True
        return False

    def recycle_session(self):
        now = time.time()
        deleting_sessions = [s for s in self.sessions if now - s[1] > self.age]
        for s in deleting_sessions:
            self.sessions.remove(s)
        Timer(self.recycle_interval, self.recycle_session).start()

sessions = Sessions()

class Users(object):
    def __init__(self):
        self.users = users_data

    def is_effective_user(self, user_name, password):
        return user_name in self.users and password == self.users.get(user_name)

users = Users()

# ------------------ 模板管理 ------------------
class Template(object):
    def __init__(self):
        encoding = config.get("TEMPLATE_ENCODING", "utf-8")
        with open(config['INDEX_FILE'], encoding=encoding) as f:
            self.index_html = f.read()
        with open(config['LOGIN_FILE'], encoding=encoding) as f:
            self.login_html = f.read()
        # 添加加载chat.html的代码
        with open(os.path.join('templates', 'chat.html'), encoding=encoding) as f:
            self.chat_html = f.read()

    def get_index_html(self):
        return self.index_html

    def get_login_html(self, login_failed=False):
        try:
            # 使用字符串替换而不是format_map,更灵活且不易出错
            login_html = self.login_html
            replacements = {
                '{login_failed}': '1' if login_failed else '0',
                '{timestamp}': str(int(time.time())),
                '{server_name}': config.get('SERVER_NAME', 'SilkRoad'),
                '{domain}': config.get('DOMAIN', 'localhost')
            }
            
            for old, new in replacements.items():
                login_html = login_html.replace(old, new)
            return login_html
            
        except (KeyError, ValueError) as e:
            # 如果格式化失败，记录错误并返回原始模板
            logger.error(f"登录页面格式化错误: {e}")
            return self.login_html
        
    # 添加获取chat.html的方法
    def get_chat_html(self):
        return self.chat_html

template = Template()

# ------------------ 浏览器信息伪装 ------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

# ------------------ 代理处理 ------------------
class Proxy(object):
    def __init__(self, handler):
        self.handler = handler
        # 从请求路径中提取目标 URL（假定形如 /http://... 或 /https://...）
        self.url = self.handler.path[1:]
        parse_result = parse.urlparse(self.url)
        self.scheme = parse_result.scheme
        self.netloc = parse_result.netloc
        self.site = self.scheme + '://' + self.netloc
        self.path = parse_result.path
        # 定义无效请求头列表，这些请求头会被过滤掉
        self.invalid_headers = {
            "cf-connecting-ip", "x-forwarded-for", "x-real-ip",
            "true-client-ip", "x-vercel-deployment-url", "x-vercel-forwarded-for",
            "x-forwarded-host", "x-forwarded-port", "x-forwarded-proto",
            "x-vercel-id", "baggage", "cdn-loop", "cf-ray", "cf-visitor",
            "cf-ipcountry", "cf-worker", "x-amzn-trace-id", "x-cache"
        }
        # 设置重试次数和超时时间
        self.max_retries = 3
        self.timeout = 30.0

    def proxy(self):
        # 判断是否为 WebSocket 请求，若是则调用占位处理
        if self.handler.headers.get('Upgrade', '').lower() == 'websocket':
            self.process_websocket()
            return

        self.process_request()
        content_length = int(self.handler.headers.get('Content-Length', 0))
        data = self.handler.rfile.read(content_length) if content_length > 0 else None
        # 只对GET请求尝试使用缓存
        if self.handler.command == 'GET':
            # 尝试从缓存获取响应
            cached_content, cached_headers = cache_manager.get_from_cache(self.url)
            if cached_content is not None:
                logger.info(f"使用缓存响应: {self.url}")
                # 模拟一个响应对象
                class CachedResponse:
                    def __init__(self, content, headers):
                        self.content = content
                        self.headers = headers or {}
                        self.status_code = 200
                        self.encoding = 'utf-8'
                    
                    def iter_bytes(self, chunk_size):
                        """模拟iter_bytes方法，用于分块传输"""
                        remaining = self.content
                        while remaining:
                            chunk, remaining = remaining[:chunk_size], remaining[chunk_size:]
                            yield chunk
                
                # 使用缓存的内容处理响应
                self.process_response(CachedResponse(cached_content, cached_headers))
                return
        # 添加重试逻辑
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # 复制所有请求头，并随机设置 User-Agent 以伪装客户端信息
                headers = {}
                for k, v in self.handler.headers.items():
                    if k.lower() not in self.invalid_headers:
                       headers[k] = v
                headers['User-Agent'] = random.choice(USER_AGENTS)
                
                # 配置 httpx 客户端，添加更多的 SSL 选项
                with httpx.Client(
                    verify=False, 
                    follow_redirects=False, 
                    timeout=self.timeout,
                    http2=False,  # 禁用 HTTP/2 可能会解决一些 SSL 问题
                    transport=httpx.HTTPTransport(retries=2)  # 内置重试机制
                ) as client:
                    # 若目标响应为大文件或非 HTML，则采用流式传输
                    r = client.request(method=self.handler.command, url=self.url, headers=headers, content=data)
                    # 如果请求成功，处理响应并退出重试循环
                    self.process_response(r)
                    break
            except ssl.SSLError as ssl_error:
                # 特别处理 SSL 错误
                logger.warning(f"SSL Error on attempt {retry_count+1}/{self.max_retries}: {ssl_error}")
                if "EOF occurred in violation of protocol" in str(ssl_error) and retry_count < self.max_retries - 1:
                    retry_count += 1
                    time.sleep(1)  # 短暂延迟后重试
                    continue
                else:
                    self.process_error(f"SSL Error: {ssl_error}")
                    break
            except httpx.TimeoutException as timeout_error:
                # 处理超时错误
                logger.warning(f"Timeout on attempt {retry_count+1}/{self.max_retries}: {timeout_error}")
                if retry_count < self.max_retries - 1:
                    retry_count += 1
                    time.sleep(1)
                    continue
                else:
                    self.process_error(f"Request timed out after {self.max_retries} attempts")
                    break
            except Exception as error:
                # 处理其他错误，添加更多上下文信息
                error_context = {
                    "url": self.url,
                    "method": self.handler.command,
                    "headers": str(headers)[:200] + "..." if len(str(headers)) > 200 else str(headers),
                    "retry_count": retry_count
                }
                logger.error(f"Error on attempt {retry_count+1}/{self.max_retries}: {error}, Context: {error_context}")
                self.process_error(f"请求错误: {error}")
                break

    def process_websocket(self):
        # 占位处理：后续可结合 websockets 库实现双向持续连接
        self.handler.send_error(HTTPStatus.NOT_IMPLEMENTED, "WebSocket代理尚未实现")
        logger.warning("WebSocket请求未实现：{}", self.url)

    def process_request(self):
        # 根据客户端 Connection 头判断是否启用 keep-alive
        client_conn = self.handler.headers.get('Connection', '').lower()
        conn_value = 'keep-alive' if client_conn == 'keep-alive' else 'close'
        # 修改部分请求头以突破检测与格式化
        self.modify_request_header('Referer', lambda x: x.replace(config['SERVER'], ''))
        self.modify_request_header('Origin', self.site)
        self.modify_request_header('Host', self.netloc)
        # 保留或添加 Accept-Language、Cache-Control 等常见头（示例，可扩展）
        if 'Accept-Language' not in self.handler.headers:
            self.handler.headers.add_header('Accept-Language', 'zh-CN,cn;q=0.9')
        self.modify_request_header('Accept-Encoding', 'identity')
        self.modify_request_header('Connection', conn_value)
        # 如果存在 Range 请求头，保持不变（用于断点续传）

    def process_response(self, r):
        # 获取内容类型和URL
        content_type = r.headers.get('Content-Type', '')
        url = self.url
        
        # 检查是否可缓存
        cacheable = r.status_code == 200 and self.handler.command == 'GET'
        
        # 如果响应为 HTML，则进行链接修正处理
        if "text/html" in content_type:
            # 尝试使用UTF-8编码处理文本内容
            content = self.revision_link(r.content, 'utf-8')
            try:
                # 尝试使用原始编码解码，然后转为UTF-8
                content = content.decode(r.encoding or 'utf-8').encode('utf-8')
                content_type = "text/html; charset=utf-8"
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，回退到ASCII编码（忽略错误）
                logger.warning(f"无法使用UTF-8解码内容，回退到ASCII编码: {self.url}")
                content = content.decode('ascii', errors='ignore').encode('ascii')
                content_type = "text/html; charset=ascii"
            content_length = len(content)
        else:
            # 对于非 HTML 大文件或流媒体，采用流式传输，不做链接修改
            content = r.content if r.content is not None else b''
            content_length = len(content)

        # 发送响应头
        self.handler.send_response(r.status_code)
        # 转发 Content-Range 等头，支持断点续传
        if "Content-Range" in r.headers:
            self.handler.send_header("Content-Range", r.headers["Content-Range"])
        if "location" in r.headers:
            self.handler.send_header('Location', self.revision_location(r.headers['location']))
        if "content-type" in r.headers:
            self.handler.send_header('Content-Type', r.headers['content-type'])
        if "set-cookie" in r.headers:
            self.revision_set_cookie(r.headers['set-cookie'])
        # 如果为 HTML，则使用修正后的内容长度，否则转发原始 Content-Length（如果有）
        self.handler.send_header('Content-Length', content_length)
        # 根据客户端请求决定连接是否保持
        client_conn = self.handler.headers.get('Connection', '').lower()
        conn_value = 'keep-alive' if client_conn.lower() == 'keep-alive' else 'close'
        self.handler.send_header('Connection', conn_value)
        self.handler.send_header('Access-Control-Allow-Origin', '*')
        
        # 判断是否为大文件（例如超过 1MB）或非 HTML 内容
        is_large_file = int(r.headers.get('Content-Length', 0)) > 1024 * 1024
        is_html = "text/html" in content_type
        
        # 尝试缓存响应内容（如果是可缓存的响应）
        if cacheable:
            # 对于HTML内容，缓存修正后的内容
            if is_html:
                cache_manager.save_to_cache(url, content, content_type, r.headers)
            # 对于非HTML内容或小文件，直接缓存原始内容
            elif not is_large_file:
                cache_manager.save_to_cache(url, r.content, content_type, r.headers)
            # 对于大文件，可以选择不缓存或仅缓存部分内容
            elif is_large_file and config.get('CACHE_LARGE_FILES', False):
                logger.debug(f"缓存大文件: {url}")
                cache_manager.save_to_cache(url, r.content, content_type, r.headers)
        
        if is_html and not is_large_file:
            # 对 HTML 内容进行链接修正
            content = self.revision_link(r.content, 'utf-8')
            try:
                content = content.decode(r.encoding or 'utf-8').encode('utf-8')
                content_type = "text/html; charset=utf-8"
            except UnicodeDecodeError:
                logger.warning(f"无法使用UTF-8解码内容，回退到ASCII编码: {self.url}")
                content = content.decode('ascii', errors='ignore').encode('ascii')
                content_type = "text/html; charset=ascii"
            
            self.handler.send_header('Content-Length', len(content))
            self.handler.end_headers()
            self.handler.wfile.write(content)
        else:
            # 对于大文件或非 HTML 内容，使用流式传输
            # 不设置 Content-Length，使用分块传输编码
            self.handler.send_header('Transfer-Encoding', 'chunked')
            self.handler.end_headers()
            
            # 使用 8KB 的块大小进行流式传输
            chunk_size = 8192
            for chunk in r.iter_bytes(chunk_size):
                # 写入分块大小（十六进制）
                self.handler.wfile.write(f"{len(chunk):X}\r\n".encode('ascii'))
                # 写入数据块
                self.handler.wfile.write(chunk)
                self.handler.wfile.write(b"\r\n")
            
            # 写入结束块
            self.handler.wfile.write(b"0\r\n\r\n")

    def process_error(self, error):
        self.handler.send_error(HTTPStatus.BAD_REQUEST, str(error))
        logger.error("Proxy error: {}", error)

    def modify_request_header(self, header, value):
        target_header = None
        for _header in self.handler.headers._headers:
            if _header[0].lower() == header.lower():
                target_header = _header
                break
        if target_header is not None:
            self.handler.headers._headers.remove(target_header)
            new_value = value(target_header[1]) if callable(value) else value
            self.handler.headers._headers.append((header, new_value))

    def revision_location(self, location):
        # 自动重定向原始链接为代理链接，支持 http(s)、相对和省略协议的情况
        if location.startswith('http://') or location.startswith('https://'):
            new_location = config['SERVER'] + location
        elif location.startswith('//'):
            new_location = config['SERVER'] + self.scheme + ':' + location
        elif location.startswith('/'):
            new_location = config['SERVER'] + self.site + location
        else:
            new_location = config['SERVER'] + self.site + self.path + '/' + location
        return new_location

    def revision_link(self, body, coding):
        # 对响应体中出现的链接进行修正，包括同页跳转、内链跳转、自动格式化与纠正错误链接
        if coding is None:
            return body
        # 示例规则，可根据需求扩展更多解析规则
        rules = [
            ("'{}http://", config['SERVER']),
            ('"{}http://', config['SERVER']),
            ("'{}https://", config['SERVER']),
            ('"{}https://', config['SERVER']),
            ('"{}//', config['SERVER'] + self.scheme + ':'),
            ("'{}//", config['SERVER'] + self.scheme + ':'),
            ('"{}/', config['SERVER'] + self.site),
            ("'{}/", config['SERVER'] + self.site),
        ]
        for rule in rules:
            pattern = rule[0].replace('{}', '')
            replacement = rule[0].format(rule[1]).encode('utf-8')
            body = body.replace(pattern.encode('utf-8'), replacement)
        return body

    def revision_set_cookie(self, cookies):
        # 将响应中的 set-cookie 进行调整，确保域名、路径等正确
        cookie_list = []
        half_cookie = None
        for _cookie in cookies.split(', '):
            if half_cookie is not None:
                cookie_list.append(', '.join([half_cookie, _cookie]))
                half_cookie = None
            elif 'Expires' in _cookie or 'expires' in _cookie:
                half_cookie = _cookie
            else:
                cookie_list.append(_cookie)
        for _cookie in cookie_list:
            # 过滤无效的 Cookie
            if self.is_valid_cookie(_cookie):
                self.handler.send_header('Set-Cookie', self.revision_response_cookie(_cookie))
    
    def is_valid_cookie(self, cookie):
        """检查 Cookie 是否有效"""
        # 过滤掉空值或格式不正确的 Cookie
        if not cookie or '=' not in cookie:
            return False
        # 可以添加更多的验证规则，例如检查 Cookie 名称是否符合规范
        return True

    def revision_response_cookie(self, cookie):
        # 设置 Cookie 24小时过期
        cookie = re.sub(r'(expires\=[^,;]+)', 
                        'expires=' + (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime('%a, %d %b %Y %H:%M:%S GMT'), 
                        cookie, flags=re.IGNORECASE)
        # 如果没有 expires 属性，添加 24 小时过期时间
        if 'expires=' not in cookie.lower():
            cookie += '; expires=' + (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        cookie = re.sub(r'domain\=[^,;]+', 'domain=.{}'.format(config['DOMAIN']), cookie, flags=re.IGNORECASE)
        cookie = re.sub(r'path\=\/', 'path={}/'.format('/' + self.site), cookie, flags=re.IGNORECASE)
        if config['SCHEME'] == 'http':
            cookie = re.sub(r'secure;?', '', cookie, flags=re.IGNORECASE)
        return cookie

# ------------------ HTTP 请求处理 ------------------
class SilkRoadHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # 支持持久连接

    def __init__(self, request, client_address, server):
        self.login_path = config['LOGIN_PATH']
        self.favicon_path = config['FAVICON_PATH']
        self.server_name = config['SERVER_NAME']
        self.session_cookie_name = config['SESSION_COOKIE_NAME']
        self.domain_re = re.compile(r'(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+')
        with open(config['FAVICON_FILE'], 'rb') as f:
            self.favicon_data = f.read()
        super().__init__(request, client_address, server)

    def do_GET(self):
        self.do_request()

    def do_POST(self):
        self.do_request()

    def do_HEAD(self):
        self.do_request()

    def do_request(self):
        self.pre_process_path()
        if self.is_login():
            if self.is_need_proxy():
                Proxy(self).proxy()
            else:
                self.process_original()
        else:
            self.redirect_to_login()

    def is_login(self):
        # 登录页面与 favicon 均无需验证会话
        if self.path == self.login_path or self.path == self.favicon_path:
            return True
        session = self.get_request_cookie(self.session_cookie_name)
        return sessions.is_session_exist(session)

    def process_original(self):
        if self.path == self.favicon_path:
            self.process_favicon()
        elif self.path == self.login_path:
            self.process_login()
        elif self.path == '/chat':  # 添加对/chat路径的处理
            self.process_chat()
        else:
            self.process_index()

    def process_login(self):
        if self.command == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = parse.parse_qs(parse.unquote(raw_data))
            if 'user' in parsed_data and 'password' in parsed_data:
                if users.is_effective_user(parsed_data['user'][0], parsed_data['password'][0]):
                    session = sessions.generate_new_session()
                    self.send_response(HTTPStatus.FOUND)
                    self.send_header('Location', '/')
                    # 设置会话 Cookie 24小时过期
                    expires = (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
                    self.send_header('Set-Cookie',
                                     '{}={}; expires={}; path=/; HttpOnly'
                                     .format(self.session_cookie_name, session, expires))
                    self.end_headers()
                    return
            body = template.get_login_html(login_failed=True)
        else:
            body = template.get_login_html(login_failed=False)
        self.return_html(body)

    def process_index(self):
        body = template.get_index_html()
        self.return_html(body)

    def process_chat(self):
        body = template.get_chat_html()
        self.return_html(body)

    def process_favicon(self):
        self.send_response(200)
        self.send_header('Content-Type', 'image/x-icon')
        self.end_headers()
        self.wfile.write(self.favicon_data)

    def return_html(self, body):
        encoded = body.encode(config.get("TEMPLATE_ENCODING", "utf-8"))
        self.send_response(200)
        self.send_header('Content-Length', len(encoded))
        self.send_header('Content-Type', 'text/html; charset={}'.format(config.get("TEMPLATE_ENCODING", "utf-8")))
        self.end_headers()
        self.wfile.write(encoded)

    def is_need_proxy(self):
        # 当请求路径以 "http://" 或 "https://" 开头时，启用代理转发
        return self.path[1:].startswith('http://') or self.path[1:].startswith('https://')

    def pre_process_path(self):
        # 支持通过 URL 参数进行跳转
        if self.path.startswith('/?url='):
            self.path = self.path.replace('/?url=', '/', 1)
        # 如果路径以域名开头，则自动补全协议
        if self.is_start_with_domain(self.path[1:]):
            self.path = '/https://' + self.path[1:]
        # 如果非代理请求，则尝试从 Referer 中补全路径
        if not self.is_need_proxy():
            referer = self.get_request_header('Referer')
            if referer is not None and parse.urlparse(referer.replace(config['SERVER'], '')).netloc != '':
                self.path = '/' + referer.replace(config['SERVER'], '') + self.path

    def get_request_cookie(self, cookie_name):
        cookies = ""
        for header in self.headers._headers:
            if header[0].lower() == 'cookie':
                cookies = header[1].split('; ')
                break
        
        # 过滤无效的 Cookie
        valid_cookies = []
        for cookie in cookies:
            parts = cookie.split('=')
            if len(parts) == 2 and parts[0] and parts[1]:  # 确保 Cookie 名和值都不为空
                valid_cookies.append(cookie)
        
        # 从有效的 Cookie 中查找目标 Cookie
        for cookie in valid_cookies:
            parts = cookie.split('=')
            if parts[0] == cookie_name:
                return parts[1]
        return ""

    def get_request_header(self, header_name):
        for header in self.headers._headers:
            if header[0].lower() == header_name.lower():
                return header[1]
        return None

    def version_string(self):
        return self.server_name

    def redirect_to_login(self):
        self.send_response(HTTPStatus.FOUND)
        self.send_header('Location', self.login_path)
        self.end_headers()

    def is_start_with_domain(self, string):
        domain = self.domain_re.match(string)
        psl = PublicSuffixList()
        if domain is None or domain.group(1)[1:] not in psl.tlds:
            return False
        return True

# ------------------ 多线程 HTTP 服务器 ------------------
class ThreadingHttpServer(ThreadingMixIn, http.server.HTTPServer):
    pass

# ------------------ 主程序入口 ------------------
if __name__ == '__main__':
    # 设置日志
    logger.add(config['LOG_FILE'], rotation="500 MB", level="INFO")
    
    # 执行系统自检和缓存清理
    system_check_and_cleanup()
    
    # 添加客户端缓存和cookie清理的响应头处理
    class ClientCacheCleaner:
        """用于清除客户端缓存和Cookie的工具类"""
        @staticmethod
        def add_cache_clearing_headers(handler):
            """添加清除缓存的HTTP头"""
            handler.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            handler.send_header('Pragma', 'no-cache')
            handler.send_header('Expires', '0')
    
    # 扩展请求处理器，添加清除客户端缓存的功能
    original_end_headers = SilkRoadHTTPRequestHandler.end_headers
    
    def custom_end_headers(self):
        """扩展end_headers方法，添加清除缓存的头"""
        if hasattr(self, 'clear_client_cache') and self.clear_client_cache:
            ClientCacheCleaner.add_cache_clearing_headers(self)
        original_end_headers(self)
    
    # 替换原始方法
    SilkRoadHTTPRequestHandler.end_headers = custom_end_headers
    
    # 在首次请求时清除客户端缓存
    original_do_request = SilkRoadHTTPRequestHandler.do_request
    
    def custom_do_request(self):
        """扩展do_request方法，在首次请求时清除客户端缓存"""
        # 标记是否需要清除客户端缓存
        self.clear_client_cache = True
        original_do_request(self)
    
    # 替换原始方法
    SilkRoadHTTPRequestHandler.do_request = custom_do_request
    
    # 启动HTTP服务器
    server_address = (config['BIND_IP'], config['PORT'])
    with ThreadingHttpServer(server_address, SilkRoadHTTPRequestHandler) as httpd:
        if config['SCHEME'] == 'https':
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=config['CERT_FILE'], keyfile=config['KEY_FILE'])
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        logger.info('系统启动完成！服务运行在 {} 端口 {} ({}://{}:{}...)',
                    config["BIND_IP"], config["PORT"], config["SCHEME"], config["DOMAIN"], config["PORT"])
        try:
            httpd.serve_forever()
        except Exception as e:
            logger.error("服务器错误: {}", e)
