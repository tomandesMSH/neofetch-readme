const { parseParams } = require("../lib/params");
const { buildSvg } = require("../lib/buildSvg");

module.exports = (req, res) => {
  const params = parseParams(req.query || {});
  const svg = buildSvg(params);

  res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400");
  res.status(200).send(svg);
};
