const { buildTimeline, frameCurve, presenceCurve, FRAME_COUNT } = require("./timeline");
const { iconManifest, escapeXml } = require("./params");
const fontBase64 = require("./font-data");

const WIDTH = 1200;
const HEIGHT = 540;
const RADIUS = 18;

const LEFT = { x: 40, y: 40, w: 460, h: 460 };
const RIGHT = { x: 540, y: 56, w: 620 };

const PALETTE = [
  "#21222c", "#ff5555", "#50fa7b", "#f1fa8c",
  "#bd93f9", "#ff79c6", "#8be9fd", "#f8f8f2",
  "#4b4d5c", "#ff7a7a", "#79ffb0", "#f4ffb0",
  "#d1b3ff", "#ffa3dd", "#b3f3ff", "#ffffff",
];

function buildLeftPanel(icons, timeline) {
  // All frames of all icons share one native size; scale uniformly to
  // fit inside LEFT while leaving room for the name label underneath.
  const native = iconManifest[icons[0]];
  const maxArtH = LEFT.h - 56;
  const scale = Math.min((LEFT.w - 40) / native.width, maxArtH / native.height);
  const artW = native.width * scale;
  const artH = native.height * scale;
  const artX = LEFT.x + (LEFT.w - artW) / 2;
  const artY = LEFT.y + 10;

  let images = "";
  let labels = "";

  icons.forEach((slug, i) => {
    const entry = iconManifest[slug];
    for (let f = 0; f < FRAME_COUNT; f++) {
      const curve = frameCurve(timeline, i, f);
      images += `<image x="${artX.toFixed(1)}" y="${artY.toFixed(1)}" width="${artW.toFixed(1)}" height="${artH.toFixed(1)}" href="${entry.frames[f]}" opacity="0">` +
        `<animate attributeName="opacity" keyTimes="${curve.keyTimes}" values="${curve.values}" dur="${timeline.duration.toFixed(3)}s" begin="0s" repeatCount="indefinite" calcMode="linear"/>` +
        `</image>\n`;
    }
    const pc = presenceCurve(timeline, i);
    const labelY = artY + artH + 34;
    labels += `<text x="${(LEFT.x + LEFT.w / 2).toFixed(1)}" y="${labelY.toFixed(1)}" text-anchor="middle" class="icon-label" fill="${entry.hex}" opacity="0">${escapeXml(entry.title)}` +
      `<animate attributeName="opacity" keyTimes="${pc.keyTimes}" values="${pc.values}" dur="${timeline.duration.toFixed(3)}s" begin="0s" repeatCount="indefinite" calcMode="linear"/>` +
      `</text>\n`;
  });

  return images + labels;
}

function buildRightPanel(params) {
  const headerY = RIGHT.y;
  let out = "";
  out += `<text x="${RIGHT.x}" y="${headerY}" class="user"><tspan fill="${params.accent}">${escapeXml(params.user)}</tspan><tspan fill="${params.text}">@${escapeXml(params.host)}</tspan></text>\n`;

  const ruleY = headerY + 14;
  const ruleW = Math.min(RIGHT.w, 44 * 9); // roughly matches the longest default header width
  out += `<line x1="${RIGHT.x}" y1="${ruleY}" x2="${RIGHT.x + ruleW}" y2="${ruleY}" stroke="${params.border}" stroke-width="2"/>\n`;

  const lineHeight = 23;
  let y = ruleY + 30;
  for (const line of params.lines) {
    out += `<text x="${RIGHT.x}" y="${y}" class="line"><tspan fill="${params.accent}">${line.label}</tspan><tspan fill="${params.border}">: </tspan><tspan fill="${params.text}">${line.value}</tspan></text>\n`;
    y += lineHeight;
  }

  // Color blocks footer, pinned near the bottom of the card.
  const blockSize = 20;
  const blockGap = 6;
  const blockY1 = HEIGHT - 76;
  const blockY2 = blockY1 + blockSize + blockGap;
  PALETTE.forEach((color, i) => {
    const row = i < 8 ? 0 : 1;
    const col = i % 8;
    const bx = RIGHT.x + col * (blockSize + blockGap);
    const by = row === 0 ? blockY1 : blockY2;
    out += `<rect x="${bx}" y="${by}" width="${blockSize}" height="${blockSize}" rx="3" fill="${color}"/>\n`;
  });

  if (params.cursor) {
    const cursorX = RIGHT.x;
    const cursorY = blockY2 + blockSize + 26;
    out += `<rect x="${cursorX}" y="${cursorY - 14}" width="10" height="18" fill="${params.accent}">` +
      `<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.45;0.5;0.95;1" dur="1.1s" begin="0s" repeatCount="indefinite"/>` +
      `</rect>\n`;
  }

  return out;
}

function buildSvg(params) {
  const timeline = buildTimeline(params.icons.length, params.speed);
  const left = buildLeftPanel(params.icons, timeline);
  const right = buildRightPanel(params);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}">
<defs>
<style>
@font-face {
  font-family: "JetBrains Mono Card";
  src: url(data:font/woff2;base64,${fontBase64}) format("woff2");
  font-weight: 400;
  font-style: normal;
}
text { font-family: "JetBrains Mono Card", ui-monospace, Consolas, monospace; }
.user { font-size: 22px; font-weight: 700; }
.line { font-size: 15px; }
.icon-label { font-size: 17px; letter-spacing: 1px; }
</style>
<clipPath id="card-clip"><rect x="0" y="0" width="${WIDTH}" height="${HEIGHT}" rx="${RADIUS}"/></clipPath>
</defs>
<g clip-path="url(#card-clip)">
<rect x="0" y="0" width="${WIDTH}" height="${HEIGHT}" fill="${params.bg}"/>
${left}
${right}
</g>
<rect x="1" y="1" width="${WIDTH - 2}" height="${HEIGHT - 2}" rx="${RADIUS}" fill="none" stroke="${params.border}" stroke-width="1.5"/>
</svg>`;
}

module.exports = { buildSvg };
