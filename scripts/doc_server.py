#!/usr/bin/env python3
"""Local Markdown doc server. Open http://127.0.0.1:7778 in browser to browse all .md files rendered as HTML."""

import http.server, os, re, urllib.parse

DOC_ROOT = r"C:\Users\Administrator\Documents\New project\docs"
PORT = 7778

CSS = """<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 750px; margin: 40px auto; padding: 20px; line-height: 1.8; color: #333; background: #fff; }
  pre { background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; }
  code { font-family: 'Fira Code', monospace; font-size: 0.9em; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th, td { border: 1px solid #ddd; padding: 10px 14px; text-align: left; }
  th { background: #f0f0f0; }
  h1, h2 { border-bottom: 2px solid #eee; padding-bottom: 8px; }
  h3, h4 { margin-top: 24px; }
  hr { border: none; border-top: 1px solid #eee; margin: 24px 0; }
  a { color: #0366d6; }
  blockquote { border-left: 4px solid #ddd; padding-left: 16px; color: #666; margin: 16px 0; }
  img { max-width: 100%; }
  ul, ol { padding-left: 24px; }
  .index { background: #f9f9f9; padding: 20px; border-radius: 8px; }
  .index a { display: block; padding: 6px 0; font-size: 1.05em; }
  .index .date { color: #999; font-size: 0.8em; margin-left: 12px; }
  .breadcrumb { color: #999; margin-bottom: 16px; font-size: 0.9em; }
</style>"""

JS = """<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>document.getElementById('content').innerHTML = marked.parse(document.getElementById('raw').textContent);</script>"""

HEADER = """<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Docs - XHLS</title>""" + CSS + "</head><body>"

def md_to_html(path):
    with open(path, 'r', encoding='utf-8') as f:
        md = f.read()
    return HEADER + '<div class="breadcrumb">📄 ' + os.path.basename(path) + '</div><div id="content"></div><script id="raw" type="text/markdown">' + md.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</script>' + JS + '</body></html>'

def build_index():
    items = []
    for f in sorted(os.listdir(DOC_ROOT), reverse=True):
        if f.endswith('.md'):
            full = os.path.join(DOC_ROOT, f)
            mtime = os.path.getmtime(full)
            import time
            date = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
            items.append(f'<a href="/{f}">📄 {f}</a><span class="date">{date}</span>')
    return HEADER + '<h1>📚 XHLS 文档库</h1><div class="index">' + '\n'.join(items) + '</div></body></html>'

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.lstrip('/')
        if path == '' or path == 'index.html':
            html = build_index().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html)
        elif path.endswith('.md'):
            filepath = os.path.join(DOC_ROOT, path)
            if os.path.exists(filepath):
                html = md_to_html(filepath).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    print(f'Doc server on http://127.0.0.1:{PORT}')
    http.server.HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
