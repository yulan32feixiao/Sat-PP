#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速本地服务器：多线程 + 文本gzip + 304缓存。

比 `python3 -m http.server` 快在：
  1. 多线程 —— 首页要并发拉 index.html / bank.bin / mock2026.bin / katex
  2. 文本类即时 gzip（html/js/css/svg）
  3. 静态资源带 Cache-Control + If-Modified-Since 304，二刷不重传

用法: python3 tools/serve.py [端口]   （默认 8000，被占用自动换 8080）
"""
import gzip
import os
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GZIP_TYPES = {".html": "text/html; charset=utf-8",
              ".js": "application/javascript; charset=utf-8",
              ".css": "text/css; charset=utf-8",
              ".svg": "image/svg+xml",
              ".json": "application/json; charset=utf-8"}
# 字体/图片可长缓存；bin 是题库数据，必须每次重验（更新题库后用户立刻拿到新题）
LONG_CACHE = {".woff2", ".png", ".jpg", ".jpeg", ".gif", ".ico"}
REVALIDATE = {".bin"}


class FastHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        path = self.translate_path(self.path)
        ext = os.path.splitext(path)[1].lower()
        if os.path.isfile(path):
            if ext in LONG_CACHE:
                self.send_header("Cache-Control", "public, max-age=86400")
            elif ext in REVALIDATE:
                self.send_header("Cache-Control", "no-cache")   # 每次带条件请求，更新后立刻生效
            elif ext in GZIP_TYPES:
                self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        # gzip 只对文本且客户端声明支持时启用
        if "gzip" in (self.headers.get("Accept-Encoding") or ""):
            path = self.translate_path(self.path)
            ext = os.path.splitext(path)[1].lower()
            if ext in GZIP_TYPES and os.path.isfile(path):
                with open(path, "rb") as f:
                    body = f.read()
                gz = gzip.compress(body, 6)
                self.send_response(200)
                self.send_header("Content-Type", GZIP_TYPES[ext])
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(gz)))
                self.send_header("Vary", "Accept-Encoding")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(gz)
                return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass  # 安静模式；要看访问日志注释掉这行


def pick_port(default):
    import socket
    for port in (default, default + 80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return default


def main():
    port = pick_port(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(("0.0.0.0", port), FastHandler)
    url = f"http://localhost:{port}/"
    print(f"🚀 {url}  (Ctrl+C 停止)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
