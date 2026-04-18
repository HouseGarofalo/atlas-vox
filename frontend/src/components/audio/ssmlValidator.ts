import { findTag, isSelfClosing, tagsForProvider } from "./ssmlSchema";

export interface SSMLDiagnostic {
  severity: "error" | "warning" | "info";
  message: string;
  startLine: number; // 1-based
  startColumn: number; // 1-based
  endLine: number;
  endColumn: number;
}

/**
 * Lightweight SSML validator. Catches the most common mistakes users hit:
 *  - unknown tag names
 *  - tags not supported by the selected provider
 *  - attributes not declared in the schema
 *  - mismatched open/close tags
 * Not a full XML parser — we deliberately keep this permissive so users
 * aren't blocked by CDATA quirks or namespace edge-cases.
 */
export function validateSSML(
  text: string,
  providerName: string | null | undefined,
): SSMLDiagnostic[] {
  const diagnostics: SSMLDiagnostic[] = [];
  const allowed = new Set(tagsForProvider(providerName).map((t) => t.name));

  const lines = text.split(/\r?\n/);
  // Stack of open tags for mismatch detection. Entry = {name, line, col}.
  const stack: Array<{ name: string; line: number; col: number }> = [];

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    // Match each tag occurrence on the line.
    const re = /<\s*(\/?)\s*([a-zA-Z][a-zA-Z0-9:_-]*)([^<>]*?)(\/?)>/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(line)) !== null) {
      const [, slash, tagName, attrs, selfSlash] = m;
      const startCol = m.index + 1;
      const endCol = m.index + m[0].length + 1;
      const tagLower = tagName;
      const schemaTag = findTag(tagLower);

      if (slash) {
        // Closing tag.
        if (!schemaTag) {
          diagnostics.push({
            severity: "error",
            message: `Unknown SSML tag </${tagLower}>`,
            startLine: li + 1,
            startColumn: startCol,
            endLine: li + 1,
            endColumn: endCol,
          });
        }
        if (stack.length === 0 || stack[stack.length - 1].name !== tagLower) {
          diagnostics.push({
            severity: "error",
            message: `Mismatched closing tag </${tagLower}> — no matching <${tagLower}>.`,
            startLine: li + 1,
            startColumn: startCol,
            endLine: li + 1,
            endColumn: endCol,
          });
        } else {
          stack.pop();
        }
        continue;
      }

      // Opening tag (possibly self-closing).
      if (!schemaTag) {
        diagnostics.push({
          severity: "error",
          message: `Unknown SSML tag <${tagLower}>`,
          startLine: li + 1,
          startColumn: startCol,
          endLine: li + 1,
          endColumn: endCol,
        });
      } else if (!allowed.has(schemaTag.name)) {
        diagnostics.push({
          severity: "warning",
          message:
            providerName
              ? `<${tagLower}> is not supported by provider "${providerName}" and will likely be ignored.`
              : `<${tagLower}> is a provider-specific extension.`,
          startLine: li + 1,
          startColumn: startCol,
          endLine: li + 1,
          endColumn: endCol,
        });
      }

      // Attribute validation.
      if (schemaTag) {
        const declared = new Set(schemaTag.attributes.map((a) => a.name));
        const attrRe = /([a-zA-Z:_-][a-zA-Z0-9:._-]*)\s*=\s*"([^"]*)"/g;
        let am: RegExpExecArray | null;
        while ((am = attrRe.exec(attrs)) !== null) {
          const attrName = am[1];
          if (!declared.has(attrName) && declared.size > 0) {
            diagnostics.push({
              severity: "warning",
              message: `Attribute "${attrName}" is not declared on <${tagLower}>.`,
              startLine: li + 1,
              startColumn: startCol,
              endLine: li + 1,
              endColumn: endCol,
            });
          }
        }
      }

      if (selfSlash || isSelfClosing(tagLower)) {
        continue;
      }
      stack.push({ name: tagLower, line: li + 1, col: startCol });
    }
  }

  // Any unclosed tags → errors at the opening location.
  for (const open of stack) {
    diagnostics.push({
      severity: "error",
      message: `Unclosed tag <${open.name}>`,
      startLine: open.line,
      startColumn: open.col,
      endLine: open.line,
      endColumn: open.col + open.name.length + 2,
    });
  }

  return diagnostics;
}
