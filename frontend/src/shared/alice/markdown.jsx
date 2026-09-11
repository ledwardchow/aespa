import { normalizeAliceText } from "./text.js";
import { cloneElement } from "react";

import { markdownText } from "../lib/markdown.js";

export const renderMarkdown = (text) => {
  text = normalizeAliceText(text);
  if (!text) return "";
  if (typeof text !== "string") text = markdownText(text);
  if (!text) return "";
  const lines = text.split("\n");
  const elements = [];
  let inList = false;
  let listItems = [];
  let codeBlockContent = [];
  let inCodeBlock = false;
  let codeBlockLang = "";
  const renderTextWithFormatting = (txt) => {
    const inlineRegex = /(`[^`]+`|\*\*[^*]+\*\*)/g;
    const segments = txt.split(inlineRegex);
    return segments.map((seg, _idx) => {
      if (seg.startsWith("`") && seg.endsWith("`")) {
        return (
          <code key={_idx} className="alice-inline-code">
            {seg.slice(1, -1)}
          </code>
        );
      }
      if (seg.startsWith("**") && seg.endsWith("**")) {
        return (
          <strong key={_idx} className="alice-bold-text">
            {seg.slice(2, -2)}
          </strong>
        );
      }
      return seg;
    });
  };
  const parseTableRow = (rowText) => {
    const cells = rowText.split("|").map((c) => c.trim());
    if (cells[0] === "") cells.shift();
    if (cells[cells.length - 1] === "") cells.pop();
    return cells;
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Code blocks
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        inCodeBlock = false;
        elements.push(
          <div className="alice-code-block-wrapper">
            <div className="alice-code-block-header">
              <span className="alice-code-block-lang">{codeBlockLang || "text"}</span>
            </div>
            <pre className="alice-code-block">
              <code>{codeBlockContent.join("\n")}</code>
            </pre>
          </div>,
        );
        codeBlockContent = [];
      } else {
        if (inList) {
          elements.push(
            <ul className="alice-markdown-list">
              {listItems.map((item, li) => (
                <li key={li}>{renderTextWithFormatting(item)}</li>
              ))}
            </ul>,
          );
          inList = false;
          listItems = [];
        }
        inCodeBlock = true;
        codeBlockLang = line.slice(3).trim();
      }
      continue;
    }
    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    // Tables
    if (trimmed.startsWith("|")) {
      if (inList) {
        elements.push(
          <ul className="alice-markdown-list">
            {listItems.map((item, li) => (
              <li key={li}>{renderTextWithFormatting(item)}</li>
            ))}
          </ul>,
        );
        inList = false;
        listItems = [];
      }
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }
      i--; // Adjust loop counter

      if (tableLines.length >= 2) {
        const headers = parseTableRow(tableLines[0]);
        const rows = [];
        const bodyLines = tableLines.slice(2);
        for (const rLine of bodyLines) {
          if (rLine.includes("---")) continue;
          rows.push(parseTableRow(rLine));
        }
        elements.push(
          <div className="alice-table-wrapper">
            <table className="alice-table">
              <thead>
                <tr>
                  {headers.map((h, hi) => (
                    <th key={hi}>{renderTextWithFormatting(h)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci}>{renderTextWithFormatting(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>,
        );
        continue;
      }
    }

    // Headers
    if (trimmed.startsWith("### ")) {
      if (inList) {
        elements.push(
          <ul className="alice-markdown-list">
            {listItems.map((item, li) => (
              <li key={li}>{renderTextWithFormatting(item)}</li>
            ))}
          </ul>,
        );
        inList = false;
        listItems = [];
      }
      elements.push(<h4 className="alice-md-h3">{renderTextWithFormatting(trimmed.slice(4))}</h4>);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      if (inList) {
        elements.push(
          <ul className="alice-markdown-list">
            {listItems.map((item, li) => (
              <li key={li}>{renderTextWithFormatting(item)}</li>
            ))}
          </ul>,
        );
        inList = false;
        listItems = [];
      }
      elements.push(<h3 className="alice-md-h2">{renderTextWithFormatting(trimmed.slice(3))}</h3>);
      continue;
    }

    // Lists
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      inList = true;
      listItems.push(trimmed.slice(2));
      continue;
    }

    // Paragraph
    if (trimmed === "") {
      if (inList) {
        elements.push(
          <ul className="alice-markdown-list">
            {listItems.map((item, li) => (
              <li key={li}>{renderTextWithFormatting(item)}</li>
            ))}
          </ul>,
        );
        inList = false;
        listItems = [];
      }
      elements.push(<div className="alice-md-space"></div>);
    } else {
      if (inList) {
        elements.push(
          <ul className="alice-markdown-list">
            {listItems.map((item, li) => (
              <li key={li}>{renderTextWithFormatting(item)}</li>
            ))}
          </ul>,
        );
        inList = false;
        listItems = [];
      }
      elements.push(<p className="alice-md-p">{renderTextWithFormatting(line)}</p>);
    }
  }
  if (inList) {
    elements.push(
      <ul className="alice-markdown-list">
        {listItems.map((item, li) => (
          <li key={li}>{renderTextWithFormatting(item)}</li>
        ))}
      </ul>,
    );
  }
  if (inCodeBlock && codeBlockContent.length > 0) {
    elements.push(
      <div className="alice-code-block-wrapper">
        <div className="alice-code-block-header">
          <span className="alice-code-block-lang">{codeBlockLang || "text"}</span>
        </div>
        <pre className="alice-code-block">
          <code>{codeBlockContent.join("\n")}</code>
        </pre>
      </div>,
    );
  }
  // Each pushed node is an array child at the call site, so give it a stable key.
  return elements.map((el, i) => cloneElement(el, { key: i }));
};
