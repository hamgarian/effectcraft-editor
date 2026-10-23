// Footage editing helpers: cut real clips into an edit. Needs jsx/helpers.jsx first (#include both, then bundle).
// Analysis (scene cuts, silences, beat cuts, colour match, reframe) comes from scripts/footage.py as JSON.
// Times are comp seconds unless named src*. A "cut" is {file, in, out[, at, speed, transition]} in SOURCE seconds.

var _FOOT = {};
function importFootage(path) {
  if (typeof path != "string") return path;   // already an item
  if (!_FOOT[path]) _FOOT[path] = app.project.importFile(new ImportOptions(new File(path)));
  return _FOOT[path];
}

// scale a layer to cover (fill, crop) or contain (fit, bars) the comp
function fitLayer(l, c, mode) {
  var src = l.source, k = (mode == "contain" ? Math.min : Math.max)(c.width / src.width, c.height / src.height) * 100;
  P(l, "Scale").setValue([k, k]); P(l, "Position").setValue([c.width / 2, c.height / 2]);
  return l;
}

// one trimmed clip: source srcIn..srcOut placed at comp time `at`. o: {fit: "cover"|"contain"|false, name, speed}
function placeClip(c, file, srcIn, srcOut, at, o) {
  o = o || {};
  var l = c.layers.add(importFootage(file));
  if (o.name) l.name = o.name;
  var sp = o.speed || 1;
  if (sp != 1) l.stretch = 100 / sp;
  l.startTime = at - srcIn / sp; l.inPoint = at; l.outPoint = at + (srcOut - srcIn) / sp;
  if (o.fit !== false) fitLayer(l, c, o.fit || "cover");
  return l;
}

// cut list -> timeline. Items without `at` go back to back. o: {start, transition, dur (s), fit}
// transition per item (or o.transition): "cut" | "crossfade" | "dip" | "whip" | "zoom" | "slide" | "glitch"
function assemble(c, cuts, o) {
  o = o || {};
  var t = o.start || 0, layers = [], extras = [];
  for (var i = 0; i < cuts.length; i++) {
    var k = cuts[i], tr = k.transition || o.transition || "cut", dur = k.dur || o.dur || 0.4;
    var overlap = (i > 0 && (tr == "crossfade" || tr == "zoom" || tr == "slide")) ? dur : 0;
    var at = k.at !== undefined ? k.at : t - overlap;
    var l = placeClip(c, k.file, k["in"], k.out, at, { fit: o.fit, speed: k.speed, name: "clip " + (i + 1) });
    if (i > 0) { var x = transition(c, layers[i - 1], l, tr, dur); if (x) extras.push(x); }
    layers.push(l); t = l.outPoint;
  }
  // later clips above earlier ones (an incoming clip fades in OVER the outgoing one); dips above all clips
  for (var j = 0; j < layers.length; j++) layers[j].moveToBeginning();
  for (var e = 0; e < extras.length; e++) extras[e].moveToBeginning();
  return { layers: layers, end: t };
}

function transition(c, a, b, kind, dur) {
  var w = c.width, h = c.height, f = 1 / FPS, t = b.inPoint;
  if (kind == "crossfade") K(P(b, "Opacity"), [[t, 0], [t + dur, 100]], "soft");
  else if (kind == "dip") return dipTo(c, a, b, dur, "#000000");   // a layer above the clips: assemble re-stacks it
  else if (kind == "whip") whipCut(c, a, b, 1);
  else if (kind == "zoom") {
    K(P(a, "Scale"), [[a.outPoint - dur, P(a, "Scale").value], [a.outPoint, mul(P(a, "Scale").value, 2.6)]], "in");
    var rb = fx(a, "CC Radial Fast Blur", { "Amount": 0 }); if (rb) K(rb.property("Amount"), [[a.outPoint - dur, 0], [a.outPoint, 80]], "in");
    K(P(b, "Opacity"), [[t, 0], [t + f * 2, 100]], "lin");
  } else if (kind == "slide") {
    var p0 = P(b, "Position").value, pa = P(a, "Position").value;
    K(P(b, "Position"), [[t, [p0[0] + w, p0[1]]], [t + dur, p0]], "out");
    K(P(a, "Position"), [[t, pa], [t + dur, [pa[0] - w, pa[1]]]], "out");
  } else if (kind == "glitch") glitchCut(c, a, b);
}
function mul(v, k) { var r = []; for (var i = 0; i < v.length; i++) r.push(v[i] * k); return r; }

// ---------- trims and time ----------
// move what part of the source shows, keeping the layer's place in the edit
function slip(l, delta) { var i = l.inPoint, o = l.outPoint; l.startTime -= delta; l.inPoint = i; l.outPoint = o; return l; }

// constant speed: 2 = twice as fast, 0.5 = half (set frameBlending for smooth slow motion)
function setSpeed(l, speed, blend) {
  var i = l.inPoint, k = l.stretch / 100, srcIn = (i - l.startTime) / k, srcDur = (l.outPoint - i) / k;   // source seconds
  l.stretch = 100 / speed; l.startTime = i - srcIn / speed; l.inPoint = i; l.outPoint = i + srcDur / speed;
  if (blend) { try { l.frameBlendingType = FrameBlendingType.PIXEL_MOTION; } catch (e) {} }
  return l;
}

// speed ramp with time remapping: segs = [[compTime, speed], ...] from the layer's in point, piecewise constant.
// o.ease (s): smooth each speed change over that long (a real ramp instead of a step)
function speedRamp(l, segs, o) {
  o = o || {};
  var srcAt = l.inPoint - l.startTime;          // source time showing at the in point
  l.timeRemapEnabled = true;
  var tr = l.property("ADBE Time Remapping");
  while (tr.numKeys) tr.removeKey(tr.numKeys);
  var t = l.inPoint, s = srcAt, keys = [[t, s]], srcDur = l.source.duration;
  for (var i = 0; i < segs.length; i++) {
    var t1 = i + 1 < segs.length ? segs[i + 1][0] : l.outPoint + 600, sp = segs[i][1];
    var s1 = s + (t1 - Math.max(t, segs[i][0])) * sp;
    if (s1 > srcDur) { t1 = Math.max(t, segs[i][0]) + (srcDur - s) / sp; s1 = srcDur; keys.push([t1, s1]); t = t1; s = s1; break; }
    keys.push([t1, s1]); t = t1; s = s1;
  }
  for (var k = 0; k < keys.length; k++) tr.setValueAtTime(keys[k][0], keys[k][1]);
  for (var j = 1; j <= tr.numKeys; j++) {
    try { if (o.ease) setEase(tr, j, 60); else tr.setInterpolationTypeAtKey(j, KeyframeInterpolationType.LINEAR); } catch (e) {}
  }
  l.outPoint = keys[keys.length - 1][0];
  if (o.blend) { try { l.frameBlendingType = FrameBlendingType.PIXEL_MOTION; } catch (e) {} }
  return keys;
}

// hold the frame at comp time `at` for `dur` seconds, then carry on (the rest shifts later by dur)
function freezeFrame(l, at, dur) {
  var srcIn = l.inPoint - l.startTime, srcAt = at - l.startTime, out = l.outPoint, srcOut = out - l.startTime, i = l.inPoint;
  l.timeRemapEnabled = true;
  var tr = l.property("ADBE Time Remapping");
  while (tr.numKeys) tr.removeKey(tr.numKeys);
  tr.setValueAtTime(i, srcIn); tr.setValueAtTime(at, srcAt); tr.setValueAtTime(at + dur, srcAt); tr.setValueAtTime(out + dur, srcOut);
  for (var j = 1; j <= tr.numKeys; j++) tr.setInterpolationTypeAtKey(j, KeyframeInterpolationType.LINEAR);
  tr.setInterpolationTypeAtKey(tr.nearestKeyIndex(at), KeyframeInterpolationType.HOLD);
  l.inPoint = i; l.outPoint = out + dur;
  return l;
}

// play the clip backwards over the same span
function reverseClip(l) {
  var i = l.inPoint, o = l.outPoint, srcIn = l.inPoint - l.startTime, srcOut = l.outPoint - l.startTime;
  l.timeRemapEnabled = true;
  var tr = l.property("ADBE Time Remapping");
  while (tr.numKeys) tr.removeKey(tr.numKeys);
  tr.setValueAtTime(i, srcOut - 1 / FPS); tr.setValueAtTime(o, srcIn);
  for (var j = 1; j <= tr.numKeys; j++) tr.setInterpolationTypeAtKey(j, KeyframeInterpolationType.LINEAR);
  l.inPoint = i; l.outPoint = o;
  return l;
}

// ---------- audio ----------
function levels(l) { return l.property("ADBE Audio Group").property("ADBE Audio Levels"); }
function audioOnlyCopy(c, l) {
  var d = c.layers.add(l.source); d.startTime = l.startTime; d.stretch = l.stretch; d.enabled = false; d.name = l.name + " audio";
  return d;
}
// J-cut: b's sound starts `lead` s before its picture (we hear the next scene first)
function jCut(c, a, b, lead) {
  var d = audioOnlyCopy(c, b); d.inPoint = b.inPoint - lead; d.outPoint = b.outPoint; b.audioEnabled = false;
  if (a) { var la = levels(a); la.setValueAtTime(b.inPoint - lead, [0, 0]); la.setValueAtTime(b.inPoint, [-48, -48]); }
  return d;
}
// L-cut: a's sound carries `lag` s over b's picture
function lCut(c, a, b, lag) {
  var d = audioOnlyCopy(c, a); d.inPoint = a.inPoint; d.outPoint = a.outPoint + lag; a.audioEnabled = false;
  if (b) { var lb = levels(b); lb.setValueAtTime(b.inPoint, [-48, -48]); lb.setValueAtTime(b.inPoint + lag, [0, 0]); }
  return d;
}
function audioFade(l, inDur, outDur) {
  var p = levels(l);
  if (inDur) { p.setValueAtTime(l.inPoint, [-48, -48]); p.setValueAtTime(l.inPoint + inDur, [0, 0]); }
  if (outDur) { p.setValueAtTime(l.outPoint - outDur, [0, 0]); p.setValueAtTime(l.outPoint, [-48, -48]); }
  return l;
}
// lower the music under speech: ranges = [[t0, t1], ...] (e.g. footage.py silences' kept ranges, placed)
function duck(music, ranges, depth, ramp) {
  var p = levels(music), d = depth || -12, r = ramp || 0.25;
  p.setValueAtTime(0, [0, 0]);
  for (var i = 0; i < ranges.length; i++) {
    p.setValueAtTime(Math.max(0, ranges[i][0] - r), [0, 0]); p.setValueAtTime(ranges[i][0], [d, d]);
    p.setValueAtTime(ranges[i][1], [d, d]); p.setValueAtTime(ranges[i][1] + r, [0, 0]);
  }
  return music;
}

// ---------- transitions ----------
function dipTo(c, a, b, dur, col) {
  var s = c.layers.addSolid(hex(col || "#000000"), "dip", c.width, c.height, 1), t = b.inPoint;
  s.inPoint = t - dur; s.outPoint = t + dur;
  K(P(s, "Opacity"), [[t - dur, 0], [t, 100], [t + dur, 0]], "soft");
  return s;
}
// the whip grammar: outgoing sharp to its last frame, ONE blurred whip frame, incoming lands sharp
function whipCut(c, a, b, dir) {
  var f = 1 / FPS, t = b.inPoint, pa = P(a, "Position").value, d = (dir || 1) * c.width * 0.35;
  K(P(a, "Position"), [[a.inPoint, pa], [t - f, [pa[0] - d, pa[1]]]], "hold");   // the shift lands ON the last frame
  var mb = fx(a, "ADBE Motion Blur", { "Direction": 90, "Blur Length": 0 });
  if (mb) K(mb.property("Blur Length"), [[0, 0], [t - f, 220]], "hold");
  a.outPoint = t; return a;
}
function glitchCut(c, a, b) {
  var f = 1 / FPS, t = b.inPoint;
  var g = fx(b, "ADBE Turbulent Displace", { "Amount": 0, "Size": 12 });
  if (g) K(g.property("Amount"), [[t, 80], [t + f, 30], [t + 2 * f, 0]], "hold");
  var pb = P(b, "Position").value;
  K(P(b, "Position"), [[t, [pb[0] + 24, pb[1]]], [t + f, [pb[0] - 12, pb[1]]], [t + 2 * f, pb]], "hold");
  return b;
}

// ---------- framing ----------
// jump-cut punch-in: from `t`, the shot is `scale`% (hold), centred on `center` (layer space), for talking heads
function punchIn(l, t, scale, center) {
  var s0 = P(l, "Scale").value, k = scale / 100;
  K(P(l, "Scale"), [[l.inPoint, s0], [t, [s0[0] * k, s0[1] * k]]], "hold");
  if (center) {
    var a = P(l, "Anchor Point").value, p = P(l, "Position").value;
    K(P(l, "Anchor Point"), [[l.inPoint, a], [t, center]], "hold");
    K(P(l, "Position"), [[l.inPoint, p], [t, p]], "hold");
  }
  return l;
}
function kenBurns(l, from, to) {   // from/to: {scale: %, pos: [x, y]}
  K(P(l, "Scale"), [[l.inPoint, [from.scale, from.scale]], [l.outPoint, [to.scale, to.scale]]], "lin");
  if (from.pos) K(P(l, "Position"), [[l.inPoint, from.pos], [l.outPoint, to.pos]], "lin");
  return l;
}
// picture in picture: rect = [x, y, w, h] in comp pixels. o: {radius, border: "#fff", borderW, shadow}
function pip(c, l, rect, o) {
  o = o || {};
  var src = l.source, k = Math.max(rect[2] / src.width, rect[3] / src.height) * 100;
  P(l, "Scale").setValue([k, k]); P(l, "Position").setValue([rect[0] + rect[2] / 2, rect[1] + rect[3] / 2]);
  var hw = rect[2] / 2 * 100 / k, hh = rect[3] / 2 * 100 / k, cx = src.width / 2, cy = src.height / 2;
  mask(l, [[cx - hw, cy - hh], [cx + hw, cy - hh], [cx + hw, cy + hh], [cx - hw, cy + hh]], {});
  if (o.shadow !== false) fx(l, "ADBE Drop Shadow", { "Opacity": 50, "Distance": 8, "Softness": 20 });
  if (o.border) {
    var b = c.layers.addShape(); b.name = "pip border"; P(b, "Position").setValue([rect[0] + rect[2] / 2, rect[1] + rect[3] / 2]);
    var g = shapeGroup(b, "border"), r = g.addProperty("ADBE Vector Shape - Rect"); r.property("Size").setValue([rect[2], rect[3]]);
    if (o.radius) r.property("Roundness").setValue(o.radius);
    var st = g.addProperty("ADBE Vector Graphic - Stroke"); st.property("Color").setValue(hex(o.border)); st.property("Stroke Width").setValue(o.borderW || 6);
    b.moveBefore(l);
  }
  return l;
}
// several layers side by side: layout "h2" (left|right), "v2" (top/bottom), "grid4"
function splitScreen(c, ls, layout, gap) {
  var g = gap || 0, W = c.width, H = c.height, cells = [];
  if (layout == "v2") cells = [[0, 0, W, H / 2 - g / 2], [0, H / 2 + g / 2, W, H / 2 - g / 2]];
  else if (layout == "grid4") cells = [[0, 0, W / 2 - g / 2, H / 2 - g / 2], [W / 2 + g / 2, 0, W / 2 - g / 2, H / 2 - g / 2],
                                       [0, H / 2 + g / 2, W / 2 - g / 2, H / 2 - g / 2], [W / 2 + g / 2, H / 2 + g / 2, W / 2 - g / 2, H / 2 - g / 2]];
  else cells = [[0, 0, W / 2 - g / 2, H], [W / 2 + g / 2, 0, W / 2 - g / 2, H]];
  for (var i = 0; i < ls.length && i < cells.length; i++) pip(c, ls[i], cells[i], { shadow: false });
  return cells;
}
// follow the subject in a vertical/square comp: keys from `footage.py reframe` ({source:[W,H], center_x:[[t, x], ...]})
function applyReframe(c, l, rf) {
  var k = c.height / rf.source[1] * 100, p = P(l, "Position");
  P(l, "Scale").setValue([k, k]);
  var keys = [];
  for (var i = 0; i < rf.center_x.length; i++) keys.push([l.startTime + rf.center_x[i][0], [c.width / 2 + (rf.source[0] / 2 - rf.center_x[i][1]) * k / 100, c.height / 2]]);
  K(p, keys, "lin");
  return l;
}

// ---------- look ----------
// match a clip to a reference: `match` from `footage.py colormatch` ({levels: {Red: {...}, Green: {...}, Blue: {...}}})
// one Levels effect, per-channel parameters ("Red Output White"...): the visible Input/Output fields only drive the
// composite RGB, whatever the Channel menu says (setting Channel to Red and Output White changed every channel)
function matchColor(l, match) {
  var params = {}, keys = ["Input Black", "Input White", "Gamma", "Output Black", "Output White"];
  for (var n in match.levels) for (var i = 0; i < keys.length; i++) params[n + " " + keys[i]] = match.levels[n][keys[i]];
  return fx(l, "Levels", params);
}
// quick looks for a layer or an adjustment layer: "teal-orange", "warm", "cool", "bw", "faded", "punchy"
function look(l, name, amount) {
  var a = amount === undefined ? 1 : amount;
  if (name == "teal-orange") fx(l, "Color Balance", { "Shadow Blue Balance": 30 * a, "Shadow Green Balance": 10 * a, "Highlight Red Balance": 25 * a, "Highlight Blue Balance": -20 * a, "Preserve Luminosity": 1 });
  else if (name == "warm") fx(l, "Photo Filter", { "Density": 30 * a });
  else if (name == "cool") fx(l, "Photo Filter", { "Filter": 4, "Density": 30 * a });
  else if (name == "bw") fx(l, "Black & White", {});
  else if (name == "faded") { fx(l, "Levels", { "Output Black": 0.08 * a, "Output White": 1 - 0.04 * a }); fx(l, "Hue/Saturation", { "Master Saturation": -25 * a }); }
  else if (name == "punchy") { fx(l, "Levels", { "Input Black": 0.04 * a, "Input White": 1 - 0.04 * a, "Gamma": 0.95 }); fx(l, "Vibrance", { "Vibrance": 30 * a }); }
  return l;
}
// film finish on an adjustment layer over the whole comp: grain, vignette, letterbox, gate weave, flicker
function filmLook(c, o) {
  o = o || {};
  var adj = c.layers.addSolid([0.5, 0.5, 0.5], "film look", c.width, c.height, 1); adj.adjustmentLayer = true;
  fx(adj, "Noise", { "Amount of Noise": o.grain === undefined ? 8 : o.grain, "Use Color Noise": 0 });
  fx(adj, "CC Vignette", { "Amount": o.vignette === undefined ? 40 : o.vignette });
  if (o.flicker !== false) { var lv = fx(adj, "Levels", { "Output White": 1 }); if (lv) expr(lv.property("Output White"), "posterizeTime(12); random(0.96, 1)"); }
  if (o.weave !== false) expr(P(adj, "Position"), "posterizeTime(12); value + [random(-1, 1), random(-1, 1)]");
  if (o.bars) {
    var bars = c.layers.addShape(); bars.name = "letterbox"; var g = shapeGroup(bars, "bars");
    var top = g.addProperty("ADBE Vector Shape - Rect"); top.property("Size").setValue([c.width, o.bars * 2]); top.property("Position").setValue([c.width / 2, 0]);
    var bot = g.addProperty("ADBE Vector Shape - Rect"); bot.property("Size").setValue([c.width, o.bars * 2]); bot.property("Position").setValue([c.width / 2, c.height]);
    g.addProperty("ADBE Vector Graphic - Fill").property("Color").setValue([0, 0, 0]); P(bars, "Position").setValue([0, 0]);
  }
  return adj;
}
// review copies: burn the timecode in
function timecodeBurn(c) { var a = c.layers.addSolid([0, 0, 0], "timecode", c.width, c.height, 1); a.adjustmentLayer = true; fx(a, "Timecode", {}); return a; }
