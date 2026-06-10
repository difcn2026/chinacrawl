<#
.SYNOPSIS
    Opens a Markdown file in the default browser with full rendering.
.DESCRIPTION
    Converts .md to a styled HTML page and opens it.
.PARAMETER Path
    Path to the .md file.
.EXAMPLE
    .\md-open.ps1 docs/v2ex-post.md
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$mdFile = Resolve-Path $Path -ErrorAction Stop
$htmlFile = [System.IO.Path]::ChangeExtension($mdFile, ".html")

$md = Get-Content $mdFile -Encoding UTF8 -Raw

# Escape backticks and dollar signs for JS template literal
$escaped = $md -replace '`', '\`' -replace '\$', '\$' -replace '\\', '\\' -replace "'", "\'"

$html = @"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>$(Split-Path -Leaf $mdFile)</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 750px; margin: 40px auto; padding: 20px; line-height: 1.8; color: #333; background: #fff; }
  pre { background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; }
  code { font-family: 'Fira Code', monospace; font-size: 0.9em; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th, td { border: 1px solid #ddd; padding: 10px 14px; text-align: left; }
  th { background: #f0f0f0; }
  h1, h2 { border-bottom: 2px solid #eee; padding-bottom: 8px; }
  hr { border: none; border-top: 1px solid #eee; margin: 24px 0; }
  a { color: #0366d6; }
  blockquote { border-left: 4px solid #ddd; padding-left: 16px; color: #666; margin: 16px 0; }
  img { max-width: 100%; }
</style>
</head>
<body>
<div id="content"></div>
<script>
  document.getElementById('content').innerHTML = marked.parse('$escaped');
</script>
</body>
</html>
"@

$html | Out-File -Encoding UTF8 $htmlFile
Write-Host "Generated: $htmlFile"
Start-Process $htmlFile
