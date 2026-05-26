import sys, io, pathlib, markdown

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

md_path = pathlib.Path(r"C:\Users\WILLIAM\prada-agent\PRADA_Culueno_2026.md")
html_path = pathlib.Path(r"C:\Users\WILLIAM\prada-agent\PRADA_Culueno_2026.html")

md_text = md_path.read_text(encoding='utf-8')

body = markdown.markdown(md_text, extensions=['tables', 'nl2br'])

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1a1a1a;
    max-width: 800px;
    margin: 0 auto;
    padding: 30px 40px 60px 40px;
}
h1 {
    font-size: 16pt;
    font-weight: bold;
    text-align: center;
    color: #1a3a1a;
    margin: 20px 0 4px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
h2 {
    font-size: 12pt;
    font-weight: bold;
    text-align: center;
    color: #1a3a1a;
    margin-bottom: 6px;
}
h2 + p em {
    display: block;
    text-align: center;
    color: #444;
    font-style: normal;
    margin-bottom: 24px;
}
h3 {
    font-size: 11pt;
    font-weight: bold;
    color: #1a3a1a;
    margin: 22px 0 6px 0;
    border-left: 4px solid #2e7d32;
    padding-left: 8px;
}
h4 {
    font-size: 11pt;
    font-weight: bold;
    color: #2e5e2e;
    margin: 16px 0 5px 0;
}
hr {
    border: none;
    border-top: 1.5px solid #2e7d32;
    margin: 28px 0;
}
p { margin: 6px 0; }
ul, ol { margin: 6px 0 6px 22px; }
li { margin: 3px 0; }
em { font-style: italic; }
strong { font-weight: bold; }
blockquote {
    background: #f0f7f0;
    border-left: 4px solid #2e7d32;
    margin: 12px 0;
    padding: 8px 14px;
    font-size: 10.5pt;
    color: #2d4a2d;
}
blockquote p { margin: 0; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px 0;
    font-size: 10pt;
}
th {
    background-color: #2e7d32;
    color: white;
    padding: 7px 10px;
    text-align: left;
    font-weight: bold;
}
td {
    padding: 5px 10px;
    border-bottom: 1px solid #cde0cd;
    vertical-align: top;
}
tr:nth-child(even) td { background-color: #f4faf4; }
tr:last-child td { border-bottom: 2px solid #2e7d32; }
code {
    background: #f0f0f0;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 10pt;
}
@media print {
    body { margin: 0; padding: 20px 30px; max-width: 100%; }
    h3 { page-break-after: avoid; }
    table { page-break-inside: avoid; }
    blockquote { page-break-inside: avoid; }
}
"""

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PRADA — Fazenda Culueno</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""

html_path.write_text(html, encoding='utf-8')
print(f"HTML gerado: {html_path}")
print("Abra no browser e use Ctrl+P → 'Salvar como PDF' para exportar.")
