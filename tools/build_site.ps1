$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

python tools/render_html.py docs/learning/00_prerequisites.md `
  --out docs/learning/00_prerequisites.html `
  --title '具身智能最小前置知识' `
  --subtitle '先搭认知地图，再刷高频问答' `
  --eyebrow 'START HERE · PRE-REQUISITES' `
  --home-href '../index.html'

python tools/render_html.py docs/roadmap.md `
  --out docs/roadmap.html `
  --title '具身智能问答 · 顺序学习路线' `
  --subtitle '按知识依赖，而不是按题目频次阅读' `
  --eyebrow 'LEARNING PATH · 28 DAYS' `
  --home-href 'index.html'

Get-ChildItem docs/interviews/*.md | ForEach-Object {
  python tools/render_html.py $_.FullName `
    --out ($_.FullName -replace '\.md$', '.html') `
    --eyebrow 'EMBODIED AI INTERVIEW QA' `
    --home-href '../index.html'
}

Write-Host 'Site rebuilt in docs/'

