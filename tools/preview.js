#!/usr/bin/env node
// Renders the card locally to an .svg file using the exact same
// lib/params.js + lib/buildSvg.js code path api/svg.js runs on Vercel, so
// there is only ever one implementation of the layout/animation to keep
// in sync. Pass query-string style args after --, e.g.:
//   node tools/preview.js -- user=tomas&school=FIT&icons=javascript,react

const fs = require("fs");
const path = require("path");
const { parseParams } = require("../lib/params");
const { buildSvg } = require("../lib/buildSvg");

const argIdx = process.argv.indexOf("--");
const qs = argIdx !== -1 ? process.argv.slice(argIdx + 1).join("&") : "";
const query = Object.fromEntries(new URLSearchParams(qs));

const params = parseParams(query);
const svg = buildSvg(params);

const outPath = path.join(__dirname, "..", ".preview.svg");
fs.writeFileSync(outPath, svg);
console.log(`Wrote ${outPath} (${(svg.length / 1024).toFixed(0)} KB)`);
console.log(`Icons: ${params.icons.join(", ")}  |  cycle: ${(params.icons.length).toString()} icons`);
