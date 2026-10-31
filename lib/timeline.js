// Computes the SMIL keyTimes/values curves that drive the left-panel logo
// dissolve. Pure math, no XML/string building here (see buildSvg.js).
//
// Design: each icon owns a single 14-frame sequence (frame 0 = fully
// formed, frame 13 = mostly dissolved). The *same* sequence is played
// forward to dissolve a logo away and backward (13 -> 0) to assemble the
// *next* logo out of the scattered characters, so only one set of frames
// per icon is ever needed. Every frame layer is a stacked <image>, each
// with its own opacity envelope; crossfades come from adjacent envelopes
// overlapping, never from a hard cut.
//
// Per-icon timeline (seconds), anchored so icon 0's hold starts at t=0:
//   assemblyStart_i -> holdStart_i   : frames 13..0 play (logo assembles)
//   holdStart_i -> dissolveStart_i   : frame 0 holds static (logo fully formed)
//   dissolveStart_i -> dissolveEnd_i : frames 0..13 play (logo dissolves)
// The next icon's assemblyStart is `overlap` seconds before this icon's
// dissolveEnd, per spec ("next logo starts assembling ~0.8s before the
// previous one finishes fading").
//
// Everything repeats indefinitely via SMIL's repeatCount, so every curve
// is built as a single [0, duration] period. Events are free to land
// anywhere, including "before 0" (wrapped to the end of the previous
// lap) - wrapTime() below folds them back into [0, duration), and any
// point that lands exactly on that seam is mirrored onto *both* t=0 and
// t=duration so the loop never jumps.

const FRAME_COUNT = 14;
const TRANS = 1.6; // seconds spent dissolving/assembling
const OVERLAP = 0.8; // seconds the next assembly overlaps the current dissolve
const EPS = 1e-6;

function buildTimeline(iconCount, hold) {
  const period = hold + 2 * TRANS - OVERLAP;
  const duration = iconCount * period;
  const frameStep = TRANS / (FRAME_COUNT - 1);

  const perIcon = [];
  for (let i = 0; i < iconCount; i++) {
    const holdStart = i * period;
    const assemblyStart = holdStart - TRANS; // may be negative; wrapped later
    const dissolveStart = holdStart + hold;
    const dissolveEnd = dissolveStart + TRANS;
    perIcon.push({ assemblyStart, holdStart, dissolveStart, dissolveEnd });
  }

  return { period, duration, frameStep, perIcon };
}

function wrapTime(t, duration) {
  const w = ((t % duration) + duration) % duration;
  return w;
}

function finalizeCurve(rawPoints, duration) {
  // Fold every point into [0, duration]; anything that lands on the seam
  // (within EPS of 0 or duration) is mirrored onto *both* ends so the
  // repeating animation never has a discontinuous jump at the loop point.
  const points = [];
  for (const { t, v } of rawPoints) {
    const w = wrapTime(t, duration);
    if (w < EPS) {
      points.push({ t: 0, v });
      points.push({ t: duration, v });
    } else if (duration - w < EPS) {
      points.push({ t: duration, v });
      points.push({ t: 0, v });
    } else {
      points.push({ t: w, v });
    }
  }

  const sorted = points.sort((a, b) => a.t - b.t);
  const dedup = [];
  for (const p of sorted) {
    const prev = dedup[dedup.length - 1];
    if (prev && Math.abs(prev.t - p.t) < EPS) {
      prev.v = p.v; // coincident timestamp: last write wins
      continue;
    }
    dedup.push({ ...p });
  }

  if (!dedup.length || dedup[0].t > EPS) dedup.unshift({ t: 0, v: 0 });
  if (dedup[dedup.length - 1].t < duration - EPS) dedup.push({ t: duration, v: 0 });

  return {
    keyTimes: dedup.map((p) => (p.t / duration).toFixed(5)).join(";"),
    values: dedup.map((p) => p.v.toFixed(3)).join(";"),
  };
}

/** Opacity envelope for one specific frame image of one icon. */
function frameCurve(timeline, iconIndex, frameIndex) {
  const { frameStep, duration } = timeline;
  const { assemblyStart, holdStart, dissolveStart } = timeline.perIcon[iconIndex];
  const points = [];

  if (frameIndex === 0) {
    // Plateau: rises into the hold, stays flat through it, falls as the
    // dissolve begins.
    points.push({ t: holdStart - frameStep, v: 0 });
    points.push({ t: holdStart, v: 1 });
    points.push({ t: dissolveStart, v: 1 });
    points.push({ t: dissolveStart + frameStep, v: 0 });
  } else {
    // Assembly hump (frames play 13 -> 0, so frame f peaks at progress (13-f)/13).
    const assembleCenter = assemblyStart + ((FRAME_COUNT - 1 - frameIndex) / (FRAME_COUNT - 1)) * TRANS;
    points.push({ t: assembleCenter - frameStep, v: 0 });
    points.push({ t: assembleCenter, v: 1 });
    points.push({ t: assembleCenter + frameStep, v: 0 });

    // Dissolve hump (frames play 0 -> 13, frame f peaks at progress f/13).
    const dissolveCenter = dissolveStart + (frameIndex / (FRAME_COUNT - 1)) * TRANS;
    points.push({ t: dissolveCenter - frameStep, v: 0 });
    points.push({ t: dissolveCenter, v: 1 });
    points.push({ t: dissolveCenter + frameStep, v: 0 });
  }

  return finalizeCurve(points, duration);
}

/** Smooth whole-name-label crossfade envelope for one icon (no per-frame flicker). */
function presenceCurve(timeline, iconIndex) {
  const { duration } = timeline;
  const { assemblyStart, holdStart, dissolveStart, dissolveEnd } = timeline.perIcon[iconIndex];
  const points = [
    { t: assemblyStart, v: 0 },
    { t: holdStart, v: 1 },
    { t: dissolveStart, v: 1 },
    { t: dissolveEnd, v: 0 },
  ];
  return finalizeCurve(points, duration);
}

module.exports = { buildTimeline, frameCurve, presenceCurve, FRAME_COUNT, TRANS, OVERLAP };
