"""Convert walkthrough.md to a print-ready HTML file."""
import markdown
import re

WALKTHROUGH_PATH = "/Users/saptayh/.gemini/antigravity/brain/74a6a089-199e-4204-b1e0-48874ca65928/walkthrough.md"
OUTPUT_PATH = "/Users/saptayh/TCGNakama-1/docs/whats_hot_walkthrough.html"

with open(WALKTHROUGH_PATH, "r") as f:
    md_content = f.read()

# Convert mermaid code blocks to <pre class="mermaid"> so Mermaid.js renders them
md_content = re.sub(
    r'```mermaid\n(.*?)\n```',
    r'<pre class="mermaid" style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:24px;margin:16px 0;text-align:center">\1</pre>',
    md_content,
    flags=re.DOTALL
)

# Convert diff blocks
def convert_diff(m):
    code = m.group(1)
    lines = []
    for line in code.split('\n'):
        if line.startswith('+'):
            lines.append(f'<span style="color:#3fb950;background:#1a3a2a;display:block;padding:0 8px">{line}</span>')
        elif line.startswith('-'):
            lines.append(f'<span style="color:#f85149;background:#3a1a1a;display:block;padding:0 8px">{line}</span>')
        else:
            lines.append(f'<span style="display:block;padding:0 8px">{line}</span>')
    return f'<pre style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin:12px 0;font-size:12px;overflow-x:auto;color:#c9d1d9">{"".join(lines)}</pre>'

md_content = re.sub(r'```diff\n(.*?)\n```', convert_diff, md_content, flags=re.DOTALL)

# Convert regular code blocks
def convert_code(m):
    lang = m.group(1) or ""
    code = m.group(2).replace('<', '&lt;').replace('>', '&gt;')
    return f'<pre style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin:12px 0;font-size:12px;overflow-x:auto;color:#c9d1d9"><code>{code}</code></pre>'

md_content = re.sub(r'```(\w*)\n(.*?)\n```', convert_code, md_content, flags=re.DOTALL)

# Convert markdown to HTML
html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TCG Nakama — Price Tracking Walkthrough</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.7;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background: white;
                color: #1a1a1a;
                padding: 20px;
                font-size: 11pt;
                line-height: 1.5;
            }}
            h1 {{ color: #1a1a1a !important; border-bottom-color: #ddd !important; }}
            h2 {{ color: #333 !important; }}
            h3 {{ color: #444 !important; }}
            h4 {{ color: #555 !important; }}
            strong {{ color: #1a1a1a !important; }}
            a {{ color: #0066cc !important; }}
            table {{ border-color: #ddd !important; }}
            th {{ background: #f0f0f0 !important; color: #333 !important; border-color: #ddd !important; }}
            td {{ border-color: #ddd !important; color: #333 !important; }}
            pre {{ background: #f6f8fa !important; border-color: #ddd !important; color: #333 !important; }}
            code {{ background: #f0f0f0 !important; color: #333 !important; }}
            div[style*="border-left"] {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
            .no-print {{ display: none !important; }}
            .mermaid {{ background: white !important; border-color: #ddd !important; }}
            .mermaid svg {{ max-width: 100% !important; }}
        }}
        
        h1 {{
            font-size: 28px;
            font-weight: 800;
            color: #f0f6fc;
            margin: 0 0 8px 0;
            padding-bottom: 12px;
            border-bottom: 2px solid #21262d;
        }}
        
        h2 {{
            font-size: 22px;
            font-weight: 700;
            color: #f0f6fc;
            margin: 32px 0 16px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #21262d;
        }}
        
        h3 {{
            font-size: 18px;
            font-weight: 600;
            color: #e6edf3;
            margin: 24px 0 12px 0;
        }}
        
        h4 {{
            font-size: 15px;
            font-weight: 600;
            color: #8b949e;
            margin: 16px 0 8px 0;
        }}
        
        p {{
            margin: 8px 0;
        }}
        
        a {{
            color: #58a6ff;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        strong {{
            color: #f0f6fc;
        }}
        
        code {{
            background: #1a2233;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
            color: #79c0ff;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid #21262d;
            margin: 24px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th {{
            background: #161b22;
            color: #f0f6fc;
            font-weight: 600;
            text-align: left;
            padding: 10px 14px;
            border: 1px solid #30363d;
            font-size: 13px;
        }}
        
        td {{
            padding: 10px 14px;
            border: 1px solid #30363d;
            font-size: 13px;
            vertical-align: top;
        }}
        
        tr:nth-child(even) {{
            background: rgba(255,255,255,0.02);
        }}
        
        ul, ol {{
            margin: 8px 0 8px 24px;
        }}
        
        li {{
            margin: 4px 0;
        }}
        
        /* Header banner */
        .header-banner {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%);
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 24px 32px;
            margin-bottom: 32px;
            text-align: center;
        }}
        
        .header-banner h1 {{
            border: none;
            margin: 0;
            padding: 0;
            font-size: 24px;
        }}
        
        .header-banner .subtitle {{
            color: #8b949e;
            font-size: 13px;
            margin-top: 8px;
        }}
        
        .header-banner .meta {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-top: 16px;
            font-size: 12px;
            color: #8b949e;
        }}
        
        .print-btn {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #238636;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            z-index: 100;
        }}
        
        .print-btn:hover {{
            background: #2ea043;
        }}
    </style>
</head>
<body>
    <div class="header-banner">
        <h1>📋 TCG Nakama — Implementation Walkthrough</h1>
        <div class="subtitle">What's Hot: Price Tracking System</div>
        <div class="meta">
            <span>📅 Date: February 18, 2026</span>
            <span>👤 Prepared by: Development Team</span>
            <span>✅ Status: Completed</span>
        </div>
    </div>
    
    {html_body}
    
    <div style="margin-top:48px;padding-top:24px;border-top:2px solid #21262d;text-align:center">
        <p style="color:#8b949e;font-size:12px">TCG Nakama — Price Tracking System Walkthrough • February 2026</p>
    </div>
    
    <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
    
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default', themeVariables: {{ fontSize: '15px', primaryColor: '#dbeafe', primaryBorderColor: '#3b82f6', primaryTextColor: '#1e293b', lineColor: '#64748b', secondaryColor: '#f0fdf4', tertiaryColor: '#fef3c7' }} }});
    </script>
</body>
</html>"""

import os
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w") as f:
    f.write(html_doc)

print(f"✅ Walkthrough HTML saved to: {OUTPUT_PATH}")
print(f"📂 Open in browser: file://{OUTPUT_PATH}")
