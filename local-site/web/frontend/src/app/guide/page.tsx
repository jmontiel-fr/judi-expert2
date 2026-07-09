"use client";

import { useState, useEffect } from "react";
import styles from "./guide.module.css";

/**
 * Simple Markdown to HTML converter for the expert guide.
 * Handles headings, bold, italic, code blocks, tables, lists, and horizontal rules.
 */
function markdownToHtml(md: string): string {
  const lines = md.split("\n");
  const html: string[] = [];
  let inCodeBlock = false;
  let inTable = false;
  let inList = false;
  let listType: "ul" | "ol" = "ul";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code blocks
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        html.push("</code></pre>");
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        html.push("<pre><code>");
      }
      continue;
    }
    if (inCodeBlock) {
      html.push(escapeHtml(line));
      html.push("\n");
      continue;
    }

    // Close list if not a list line
    if (inList && !line.match(/^\s*[-*]\s/) && !line.match(/^\s*\d+\.\s/) && line.trim() !== "") {
      html.push(listType === "ul" ? "</ul>" : "</ol>");
      inList = false;
    }

    // Horizontal rule
    if (line.match(/^---+$/)) {
      if (inTable) { html.push("</tbody></table>"); inTable = false; }
      html.push("<hr>");
      continue;
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.*)/);
    if (headingMatch) {
      if (inTable) { html.push("</tbody></table>"); inTable = false; }
      const level = headingMatch[1].length;
      const text = inlineFormat(headingMatch[2]);
      html.push(`<h${level}>${text}</h${level}>`);
      continue;
    }

    // Table
    if (line.includes("|") && line.trim().startsWith("|")) {
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      // Check if separator row
      if (cells.every((c) => c.match(/^[-:]+$/))) continue;

      if (!inTable) {
        inTable = true;
        html.push('<table class="' + styles.mdTable + '"><thead><tr>');
        cells.forEach((c) => html.push(`<th>${inlineFormat(c)}</th>`));
        html.push("</tr></thead><tbody>");
      } else {
        html.push("<tr>");
        cells.forEach((c) => html.push(`<td>${inlineFormat(c)}</td>`));
        html.push("</tr>");
      }
      continue;
    } else if (inTable) {
      html.push("</tbody></table>");
      inTable = false;
    }

    // Unordered list
    const ulMatch = line.match(/^(\s*)[-*]\s+(.*)/);
    if (ulMatch) {
      if (!inList) { html.push("<ul>"); inList = true; listType = "ul"; }
      html.push(`<li>${inlineFormat(ulMatch[2])}</li>`);
      continue;
    }

    // Ordered list
    const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
    if (olMatch) {
      if (!inList) { html.push("<ol>"); inList = true; listType = "ol"; }
      html.push(`<li>${inlineFormat(olMatch[2])}</li>`);
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      if (inList) { html.push(listType === "ul" ? "</ul>" : "</ol>"); inList = false; }
      continue;
    }

    // Paragraph
    html.push(`<p>${inlineFormat(line)}</p>`);
  }

  if (inList) html.push(listType === "ul" ? "</ul>" : "</ol>");
  if (inTable) html.push("</tbody></table>");
  if (inCodeBlock) html.push("</code></pre>");

  return html.join("\n");
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inlineFormat(text: string): string {
  let result = text;
  // Code inline
  result = result.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold
  result = result.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // Italic
  result = result.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return result;
}

export default function GuidePage() {
  const [html, setHtml] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/expert-guide.md")
      .then((res) => res.text())
      .then((md) => {
        setHtml(markdownToHtml(md));
        setLoading(false);
      })
      .catch(() => {
        setHtml("<p>Erreur lors du chargement du guide.</p>");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className={styles.container}>
        <p>Chargement du guide...</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div
        className={styles.content}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
