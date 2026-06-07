const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3456;
const ROOT = path.resolve(__dirname, '..');

const HTML_TPL = (title, body, files) => `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { display: flex; height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  .sidebar { width: 260px; background: #1e1e2e; color: #cdd6f4; padding: 16px 0; overflow-y: auto; flex-shrink: 0; }
  .sidebar h2 { padding: 0 16px 12px; font-size: 14px; color: #a6adc8; text-transform: uppercase; letter-spacing: 1px; }
  .sidebar a { display: block; padding: 8px 16px; color: #cdd6f4; text-decoration: none; font-size: 13px; border-left: 3px solid transparent; }
  .sidebar a:hover, .sidebar a.active { background: #313244; border-left-color: #89b4fa; color: #fff; }
  .content { flex: 1; overflow-y: auto; padding: 40px 48px; max-width: 860px; background: #fff; }
  .content h1 { font-size: 28px; margin-bottom: 8px; color: #1e1e2e; }
  .content h2 { font-size: 20px; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #e0e0e0; color: #333; }
  .content h3 { font-size: 16px; margin: 20px 0 8px; color: #555; }
  .content p { line-height: 1.8; margin: 8px 0; color: #444; }
  .content ul, .content ol { margin: 8px 0; padding-left: 24px; }
  .content li { line-height: 1.7; margin: 4px 0; color: #444; }
  .content code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #d6336c; }
  .content pre { background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; }
  .content pre code { background: none; color: inherit; padding: 0; }
  .content blockquote { border-left: 4px solid #89b4fa; padding: 4px 16px; margin: 12px 0; background: #f8f8fc; color: #666; }
  .content strong { color: #1e1e2e; }
  .content hr { border: none; border-top: 1px solid #e0e0e0; margin: 24px 0; }
  .content a { color: #89b4fa; }
  .content table { border-collapse: collapse; margin: 12px 0; width: 100%; }
  .content th, .content td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  .content th { background: #f5f5f5; }
</style>
</head>
<body>
<div class="sidebar">
  <h2>📁 项目文件</h2>
  ${files.map(f => `<a href="${f.path}"${f.active ? ' class="active"' : ''}>${f.label}</a>`).join('\n  ')}
</div>
<div class="content">${body}</div>
</body>
</html>`;

function md2html(md) {
  return md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // headers
    .replace(/^#### (.+)/gm, '<h4>$1</h4>')
    .replace(/^### (.+)/gm, '<h3>$1</h3>')
    .replace(/^## (.+)/gm, '<h2>$1</h2>')
    .replace(/^# (.+)/gm, '<h1>$1</h1>')
    // bold & italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code>${code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`)
    // inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    // images
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%">')
    // blockquote
    .replace(/^&gt; (.+)/gm, '<blockquote>$1</blockquote>')
    // hr
    .replace(/^---$/gm, '<hr>')
    // unordered lists
    .replace(/^- (.+)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    // ordered lists
    .replace(/^\d+\. (.+)/gm, '<li>$1</li>')
    // paragraphs
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[a-z/])(.+)/gm, '<p>$1</p>')
    // clean up
    .replace(/<p>\s*<\/p>/g, '')
    .replace(/<\/ul>\s*<ul>/g, '')
    .replace(/<\/blockquote>\s*<blockquote>/g, '<br>');
}

function scanFiles(dir, base = '') {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const e of entries) {
    if (e.name.startsWith('.') || e.name === 'node_modules' || e.name === 'outputs' || e.name === 'scripts') continue;
    const rel = base ? `${base}/${e.name}` : e.name;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      files.push(...scanFiles(full, rel));
    } else if (e.name.endsWith('.md')) {
      files.push({ path: '/' + rel, label: rel, full });
    }
  }
  return files;
}

function buildIndex(files) {
  const items = files.map(f => `<li><a href="${f.path}">📄 ${f.label}</a></li>`).join('\n');
  return `<h1>📚 项目 Markdown 文件</h1><p>共 ${files.length} 个文件</p><ul>${items}</ul>`;
}

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(req.url.split('?')[0]);
  const filePath = path.join(ROOT, urlPath === '/' ? '' : urlPath);

  if (urlPath === '/' || urlPath === '/index.html') {
    const files = scanFiles(ROOT);
    const body = buildIndex(files);
    const html = HTML_TPL('项目文件索引', body, [{ path: '/', label: '🏠 首页', active: true }, ...files]);
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
    return;
  }

  if (urlPath.endsWith('.md') && fs.existsSync(filePath)) {
    const md = fs.readFileSync(filePath, 'utf-8');
    const body = md2html(md);
    const files = scanFiles(ROOT);
    const activePath = urlPath;
    const navFiles = [
      { path: '/', label: '🏠 首页', active: false },
      ...files.map(f => ({ ...f, active: f.path === activePath }))
    ];
    const title = path.basename(urlPath);
    const html = HTML_TPL(title, body, navFiles);
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
    return;
  }

  res.writeHead(404);
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`MD Server running at http://localhost:${PORT}`);
});
