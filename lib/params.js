// Parses, validates and sanitizes the query-string parameters the public
// API accepts. Nothing here touches the DOM/SVG string building - see
// buildSvg.js for that. Keeping this isolated makes the "what can a user
// actually type into the URL" surface easy to audit and document.

const iconManifest = require("../generated/icon-frames.json");

const DEFAULT_ICONS = [
  "javascript", "typescript", "react", "nodedotjs",
  "php", "python", "git", "linux",
];

// Right-panel "neofetch" lines, in display order. `key` is the query
// param name, `label` is what's printed before the ":" on the card.
const LINE_FIELDS = [
  { key: "os", label: "OS" },
  { key: "school", label: "School" },
  { key: "city", label: "City" },
  { key: "frontend", label: "Frontend" },
  { key: "backend", label: "Backend" },
  { key: "web", label: "Web" },
  { key: "ai", label: "AI" },
  { key: "mobile", label: "Mobile" },
  { key: "database", label: "Database" },
  { key: "cloud", label: "Cloud" },
  { key: "devops", label: "DevOps" },
  { key: "editor", label: "Editor" },
  { key: "shell", label: "Shell" },
  { key: "terminal", label: "Terminal" },
  { key: "languages", label: "Languages" },
  { key: "projects", label: "Projects" },
  { key: "mail", label: "Mail" },
  { key: "github", label: "GitHub" },
  { key: "linkedin", label: "LinkedIn" },
  { key: "website", label: "Website" },
  { key: "status", label: "Status" },
  { key: "hobby", label: "Hobby" },
];

const MAX_LINE_VALUE_LEN = 42;
const MAX_USER_LEN = 28;
const MAX_LINES_TOTAL = 14; // predefined + extra combined, protects the card layout
const HEX_RE = /^#?[0-9a-fA-F]{6}$/;

function escapeXml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function truncate(str, max) {
  if (str.length <= max) return str;
  return str.slice(0, max - 1).trimEnd() + "…";
}

function cleanText(raw, max) {
  if (typeof raw !== "string") return "";
  // Treat literal "+" as a space, matching the x-www-form-urlencoded
  // convention most people expect when hand-typing a query string
  // (a literal "+" character must be sent as %2B).
  const oneLine = raw.replace(/\+/g, " ").replace(/[\r\n\t]+/g, " ").trim();
  return escapeXml(truncate(oneLine, max));
}

function cleanHex(raw, fallback) {
  if (typeof raw !== "string") return fallback;
  const trimmed = raw.trim();
  if (!HEX_RE.test(trimmed)) return fallback;
  return trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
}

function parseIcons(raw) {
  if (typeof raw !== "string" || !raw.trim()) return DEFAULT_ICONS;
  const slugs = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s) => s && Object.prototype.hasOwnProperty.call(iconManifest, s));
  if (!slugs.length) return DEFAULT_ICONS;
  return slugs.slice(0, 12); // keep the loop period sane
}

function parseExtra(raw) {
  if (typeof raw !== "string" || !raw.trim()) return [];
  return raw
    .split("|")
    .map((pair) => {
      const idx = pair.indexOf(":");
      if (idx === -1) return null;
      const label = cleanText(pair.slice(0, idx), 16);
      const value = cleanText(pair.slice(idx + 1), MAX_LINE_VALUE_LEN);
      if (!label || !value) return null;
      return { label, value };
    })
    .filter(Boolean)
    .slice(0, 6);
}

function parseParams(query) {
  const user = cleanText(query.user || "guest", MAX_USER_LEN) || "guest";
  const host = cleanText(query.host || "github", 20) || "github";

  const lines = [];
  for (const { key, label } of LINE_FIELDS) {
    const value = cleanText(query[key], MAX_LINE_VALUE_LEN);
    if (value) lines.push({ label, value });
    if (lines.length >= MAX_LINES_TOTAL) break;
  }
  if (lines.length < MAX_LINES_TOTAL) {
    for (const extra of parseExtra(query.extra)) {
      lines.push(extra);
      if (lines.length >= MAX_LINES_TOTAL) break;
    }
  }

  let speed = parseFloat(query.speed);
  if (!Number.isFinite(speed)) speed = 3;
  speed = Math.min(8, Math.max(1, speed));

  const cursor = query.cursor !== "off";

  return {
    user,
    host,
    lines,
    icons: parseIcons(query.icons),
    speed,
    bg: cleanHex(query.bg, "#0d0d11"),
    border: cleanHex(query.border, "#2a2a33"),
    accent: cleanHex(query.accent, "#7dd3fc"),
    text: cleanHex(query.text, "#e4e4e7"),
    cursor,
  };
}

module.exports = { parseParams, LINE_FIELDS, DEFAULT_ICONS, escapeXml, iconManifest };
