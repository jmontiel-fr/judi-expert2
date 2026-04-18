#!/usr/bin/env python3
"""Génère un PDF à partir de docs/methodologie.md en utilisant markdown + simple HTML."""

import os
import sys

def md_to_html(md_text: str) -> str:
    """Convertit du markdown basique en HTML."""
    lines = md_text.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br/>")
            continue
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("- **"):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif stripped.startswith("> "):
            html_lines.append(f"<blockquote>{stripped[2:]}</blockquote>")
        elif stripped.startswith("---"):
            html_lines.append("<hr/>")
        elif stripped.startswith("**") and stripped.endswith("**"):
            html_lines.append(f"<p><strong>{stripped[2:-2]}</strong></p>")
        else:
            # Bold inline
            import re
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_lines.append(f"<p>{text}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, "methodologie.md")
    
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_body = md_to_html(md_content)
    
    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<title>Méthodologie — Judi-Expert</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1e293b; line-height: 1.6; }}
  h1 {{ color: #1e40af; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }}
  h2 {{ color: #1e40af; margin-top: 32px; }}
  h3 {{ color: #334155; }}
  blockquote {{ border-left: 4px solid #2563eb; padding-left: 16px; color: #475569; font-style: italic; }}
  ul {{ padding-left: 24px; }}
  li {{ margin-bottom: 4px; }}
  hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }}
  strong {{ color: #1e293b; }}
  @media print {{ body {{ margin: 20px; }} }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    
    html_path = os.path.join(script_dir, "methodologie.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"HTML généré : {html_path}")
    print("Pour générer le PDF : ouvrir le HTML dans un navigateur et imprimer en PDF.")


if __name__ == "__main__":
    main()
