// Core helpers for EffectCraft build scripts (tested on EffectCraft 0.14.0 and 0.16.0, `effectcraft-cli script X.jsx --empty`).
// Headless scripts cannot #include: paste this in, or bundle with scripts/bundle.py.
// Set FPS, W, H before use.
var FPS = 20, W = 1080, H = 1080;

function hex(h) { if (typeof h != "string") return h; return [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255]; }
var seed = 7;
function rnd() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }
function rr(a, b) { return a + (b - a) * rnd(); }
function log(s) { writeLn(s); }

function comp(name, dur, bg, w, h) {
  var c = app.project.items.addComp(name, w || W, h || H, 1, dur, FPS);
  if (bg) c.layers.addSolid(hex(bg), "bg", w || W, h || H, 1);
  return c;
}

// ease influence per curve type, measured from reference camera moves:
// snap 92, out 72, soft 60, in 33, lin 4
var EASE = { snap: 92, out: 72, soft: 60, "in": 33, lin: 4 };
function setEase(p, i, infl) {
  for (var n = 1; n <= 3; n++) {
    var e = []; for (var k = 0; k < n; k++) e.push(new KeyframeEase(0, infl));
    try { p.setTemporalEaseAtKey(i, e, e); return; } catch (err) {}
  }
}
// list: [[t, v], ...]; mode: "hold" | "lin" | a key of EASE (default "out")
// keys closer than one frame merge in 0.14: keep them >= 1/FPS apart
function K(p, list, mode) {
  if (!p) { log("K: missing property, first key " + list[0][0]); return; }
  for (var i = 0; i < list.length; i++) p.setValueAtTime(list[i][0], list[i][1]);
  for (var j = 1; j <= p.numKeys; j++) {
    try {
      if (mode == "hold") p.setInterpolationTypeAtKey(j, KeyframeInterpolationType.HOLD);
      else if (mode != "lin") setEase(p, j, EASE[mode || "out"] || 72);
    } catch (err) {}
  }
}

// transform props must come from the LAYER's transform group: on shape layers a bare
// l.property("Position") resolves to the first shape group's transform instead
var TRANSFORM = { "Anchor Point": 1, "Position": 1, "Scale": 1, "Rotation": 1, "Opacity": 1, "X Rotation": 1, "Y Rotation": 1, "Z Rotation": 1, "Orientation": 1 };
function P(l, name) {
  if (TRANSFORM[name]) {
    var tg = null; try { tg = l.property("ADBE Transform Group"); } catch (e) {}
    if (tg) { var p = null; try { p = tg.property(name); } catch (e) {} if (p) return p; }
  }
  if (name == "Zoom") { try { return l.property("ADBE Camera Options Group").property("Zoom"); } catch (e) {} }
  return l.property(name);
}

// match: a display name or id from `effectcraft-cli exec effect.list` ("Hue/Saturation", "ec.color.huesaturation")
// or an AE match name ("ADBE HUE SATURATION"). A hybrid ("ADBE Hue/Saturation") matches nothing. Failures are
// collected in FX_FAILS: call fxCheck() at the end of the build so a missing effect fails it instead of hiding in the log.
var FX_FAILS = [];
function fx(l, match, params) {
  var e = null, why = "";
  try { e = l.property("Effects").addProperty(match); } catch (err) { why = String(err); }
  if (!e) { FX_FAILS.push(match + " on '" + l.name + "' " + why); log("effect failed: " + match + " on '" + l.name + "' " + why); return null; }
  for (var k in params) { try { e.property(k).setValue(params[k]); } catch (err) { FX_FAILS.push(match + "/" + k + ": " + err); log("fx param " + match + "/" + k + ": " + err); } }
  return e;
}
function fxCheck() { if (FX_FAILS.length) throw new Error(FX_FAILS.length + " effect/param failures:\n" + FX_FAILS.join("\n")); }

// startTime first, then in/out; the source comp's duration must cover the out-point or the tail renders empty
function place(main, c, t0, t1) { var l = main.layers.add(c); l.startTime = t0; l.inPoint = t0; l.outPoint = t1; return l; }

// element animates on twos/threes while the camera stays at full rate
function stepped(l, fps) { fx(l, "ADBE Posterize Time", { "Frame Rate": fps }); return l; }

// stop-motion "boil": turbulent displacement whose evolution jumps `fps` times a second
function boil(l, amt, fps) {
  var d = fx(l, "ADBE Turbulent Displace", { "Amount": amt || 4, "Size": 55, "Complexity": 2 });
  if (d) { try { d.property("Evolution").expression = "posterizeTime(" + (fps || 8) + "); random(0, 720)"; } catch (e) { log("boil expr: " + e); } }
  return l;
}

// shape layer with one group; the first group in Contents draws on top, so new groups moveTo(1)
function shapeGroup(l, name) { var g = l.property("Contents").addProperty("ADBE Vector Group"); g.name = name || "g"; try { g.moveTo(1); } catch (e) {} return g.property("Contents"); }

// dashed stroke: native in 0.14
function dashes(stroke, dash, gap) {
  var d = stroke.property("ADBE Vector Stroke Dashes");
  d.addProperty("ADBE Vector Stroke Dash 1").setValue(dash);
  d.addProperty("ADBE Vector Stroke Gap 1").setValue(gap);
}

// any engine command from a script (ids from `effectcraft-cli commands --filter X`); failures land in FX_FAILS
function run(id, params) {
  try { return app.run(id, params || {}); } catch (e) { FX_FAILS.push(id + ": " + e); log("run " + id + ": " + e); return null; }
}

// mask from points (layer space). o: {feather, mode: "add"|"subtract"|..., inverted, closed, inT, outT}
function mask(l, pts, o) {
  o = o || {};
  var m = l.property("ADBE Mask Parade").addProperty("ADBE Mask Atom"), s = new Shape();
  s.vertices = pts; s.closed = o.closed !== false;
  if (o.inT) s.inTangents = o.inT; if (o.outT) s.outTangents = o.outT;
  m.property("ADBE Mask Shape").setValue(s);
  if (o.feather) m.property("ADBE Mask Feather").setValue([o.feather, o.feather]);
  if (o.inverted) { try { m.inverted = true; } catch (e) {} }
  return m;
}

// expression on a property; returns the value at time t so a typo shows up as an error, not as a silent default
function expr(p, code, t) {
  p.expression = code;
  try { return p.valueAtTime(t || 0, false); } catch (e) { FX_FAILS.push("expression: " + code + " -> " + e); return null; }
}

// motion-track a point in footage layer `src` and pin `target` (a layer) to it.
// center: [x, y] of a high-contrast feature on the first frame (layer space). Returns the tracker status.
function trackAttach(src, target, center, o) {
  o = o || {};
  run("track.new", { layer: src.index, kind: "transform", position: true, rotation: !!o.rotation, scale: !!o.scale, target: target.index });
  run("track.setPoint", { layer: src.index, point: 1, center: center, featureSize: o.feature || [30, 30], searchSize: o.search || [80, 80] });
  run("track.analyze", { layer: src.index, direction: "forward", wait: true });
  var st = run("track.status", { layer: src.index });
  run("track.apply", { layer: src.index });
  return st;
}
// stabilize a shaky footage layer (Warp Stabilizer; blocks until analysed)
function stabilize(src) { return run("track.warpStabilizer", { layer: src.index, wait: true }); }

// burned-in captions: caps = [{t0, t1, text}] (scripts/captions.py writes them as CAPTIONS). One text layer with hold
// keys on Source Text, plus an optional box. o: {font, size, fill, pos: [x, y], box: "#000000", boxOpacity: 60}
function captionTrack(c, caps, o) {
  o = o || {};
  var l = c.layers.addText(" "), sp = l.property("Source Text"), td = sp.value;
  td.font = o.font || "Arial Black"; td.fontSize = o.size || Math.round(c.height * 0.045); td.applyFill = true; td.fillColor = hex(o.fill || "#ffffff");
  try { td.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e) {}
  sp.setValue(td); l.name = "captions";
  P(l, "Position").setValue(o.pos || [c.width / 2, c.height * 0.86]);
  sp.setValueAtTime(0, " ");
  for (var i = 0; i < caps.length; i++) { sp.setValueAtTime(caps[i].t0, caps[i].text); sp.setValueAtTime(caps[i].t1, " "); }
  for (var k = 1; k <= sp.numKeys; k++) { try { sp.setInterpolationTypeAtKey(k, KeyframeInterpolationType.HOLD); } catch (e) {} }
  if (o.box) {
    var b = c.layers.addShape(); b.name = "caption box"; P(b, "Position").setValue(o.pos || [c.width / 2, c.height * 0.86]);
    var g = shapeGroup(b, "box"), r = g.addProperty("ADBE Vector Shape - Rect");
    r.property("Size").setValue([c.width * 0.8, (o.size || c.height * 0.045) * 1.6]);
    g.addProperty("ADBE Vector Graphic - Fill").property("Color").setValue(hex(o.box));
    var op = P(b, "Opacity"); op.setValueAtTime(0, 0);
    for (var j = 0; j < caps.length; j++) { op.setValueAtTime(caps[j].t0, o.boxOpacity || 60); op.setValueAtTime(caps[j].t1, 0); }
    for (var q = 1; q <= op.numKeys; q++) { try { op.setInterpolationTypeAtKey(q, KeyframeInterpolationType.HOLD); } catch (e) {} }
    b.moveAfter(l);
  }
  return l;
}

// a rendered PNG sequence (e.g. a Blender set) as one footage layer per frame: pathFn(i) -> file path
function imageSequence(c, pathFn, n) {
  var ls = [];
  for (var i = 0; i < n; i++) {
    var f = app.project.importFile(new ImportOptions(new File(pathFn(i)))), l = c.layers.add(f);
    P(l, "Position").setValue([c.width / 2, c.height / 2]);
    P(l, "Scale").setValue([c.width / f.width * 100, c.height / f.height * 100]);
    l.inPoint = i / FPS; l.outPoint = (i + 1) / FPS; ls.push(l);
  }
  return ls;
}

// composite a cut-out INTO a plate instead of pasting it: plate comp + cut-out comp (alpha) at pos.
// match black/white points + saturation to the plate, shade for the light direction (lit at top -> darker at feet),
// light wrap (blurred plate through an edge band just inside the silhouette), cast + contact shadow, grain + softness.
// o: {black, white, sat, shadeTop, shadeBottom, castDir:[dx,dy], footY, wrap} (all optional). Returns the cut-out layer.
function compositeCutout(c, plate, cutout, pos, o) {
  o = o || {};
  var pl = c.layers.add(plate); P(pl, "Position").setValue([c.width / 2, c.height / 2]);
  var fy = o.footY || cutout.height / 2, cd = o.castDir || [60, 200];
  var cast = c.layers.addShape(); cast.name = "cast shadow"; P(cast, "Position").setValue(pos);
  var cg = shapeGroup(cast, "cast"), cp = cg.addProperty("ADBE Vector Shape - Group"), sh = new Shape();
  sh.vertices = [[-cutout.width * 0.12, fy], [cutout.width * 0.12, fy], [cutout.width * 0.12 + cd[0], fy + cd[1]], [-cutout.width * 0.12 + cd[0] * 0.8, fy + cd[1]]];
  sh.closed = true; cp.property("Path").setValue(sh);
  cg.addProperty("ADBE Vector Graphic - Fill").property("Color").setValue([0, 0, 0]);
  P(cast, "Opacity").setValue(45); fx(cast, "ADBE Gaussian Blur 2", { "Blurriness": 26 });
  var ct = c.layers.addShape(); ct.name = "contact shadow"; P(ct, "Position").setValue([pos[0], pos[1] + fy]);
  var eg = shapeGroup(ct, "contact"), el = eg.addProperty("ADBE Vector Shape - Ellipse"); el.property("Size").setValue([cutout.width * 0.4, cutout.width * 0.06]);
  eg.addProperty("ADBE Vector Graphic - Fill").property("Color").setValue([0, 0, 0]);
  P(ct, "Opacity").setValue(70); fx(ct, "ADBE Gaussian Blur 2", { "Blurriness": 8 });
  var cl = c.layers.add(cutout); P(cl, "Position").setValue(pos);
  fx(cl, "ADBE HUE SATURATION", { "Master Saturation": o.sat === undefined ? -30 : o.sat });
  fx(cl, "ADBE Easy Levels2", { "Output Black": o.black || 0.05, "Output White": o.white || 0.85, "Gamma": 0.95 });
  fx(cl, "ADBE Gaussian Blur 2", { "Blurriness": 0.8 }); fx(cl, "ADBE Noise", { "Amount of Noise": 7, "Use Color Noise": 0 });
  var shade = c.layers.addSolid([0, 0, 0], "shade", c.width, c.height, 1);
  fx(shade, "ADBE Ramp", { "Start of Ramp": [pos[0], pos[1] - cutout.height / 2], "Start Color": o.shadeTop || [0.95, 0.95, 0.95],
                           "End of Ramp": [pos[0], pos[1] + cutout.height / 2], "End Color": o.shadeBottom || [0.5, 0.48, 0.5] });
  shade.blendingMode = BlendingMode.MULTIPLY;
  var sm = c.layers.add(cutout); P(sm, "Position").setValue(pos); shade.trackMatteType = TrackMatteType.ALPHA;
  // light wrap: edge band = white silhouette minus a blurred black copy of itself
  var edge = comp(cutout.name + " edge", c.duration, "#000000", c.width, c.height);
  var ew = edge.layers.add(cutout); P(ew, "Position").setValue(pos); fx(ew, "ADBE Fill", { "Color": [1, 1, 1] });
  var eb = edge.layers.add(cutout); P(eb, "Position").setValue(pos); fx(eb, "ADBE Fill", { "Color": [0, 0, 0] }); fx(eb, "ADBE Gaussian Blur 2", { "Blurriness": 12 });
  var wrap = c.layers.add(plate); P(wrap, "Position").setValue([c.width / 2, c.height / 2]); wrap.name = "light wrap";
  fx(wrap, "ADBE Gaussian Blur 2", { "Blurriness": 40, "Repeat Edge Pixels": 1 }); fx(wrap, "ADBE Easy Levels2", { "Gamma": 1.4 });
  wrap.blendingMode = BlendingMode.SCREEN; P(wrap, "Opacity").setValue(o.wrap || 75);
  c.layers.add(edge); wrap.trackMatteType = TrackMatteType.LUMA;
  return cl;
}

// infinite background: a frame-sized solid behind every shot layer in `main`, skipping overlays
// (non-normal blend, <100% or animated opacity, or overlay-like names). Only layers named in `colours`
// get one: {layerName: "#rrggbb" | "photo"}; "photo" = a blurred 240% copy of the shot instead of a solid.
// Frame-sized is enough because the fill never moves (3x-frame solids ran 0.14 out of memory).
function infiniteBackground(main, colours) {
  var shots = [];
  for (var i = 1; i <= main.numLayers; i++) {
    var l = main.layer(i);
    if (!colours.hasOwnProperty(l.name)) continue;
    var op = P(l, "Opacity"), overlay = /flash|dim|fade|leak|wipe|whip|overlay|grain|vignette/i.test(l.name);
    try { if (l.blendingMode != BlendingMode.NORMAL) overlay = true; } catch (e) {}
    try { if (op.numKeys > 0 || op.value < 100) overlay = true; } catch (e) {}
    if (!overlay) shots.push(l);
  }
  for (var s = 0; s < shots.length; s++) {
    var sh = shots[s], col = colours[sh.name], bg;
    if (col == "photo") {
      bg = main.layers.add(sh.source); bg.startTime = sh.startTime;
      P(bg, "Scale").setValue([240, 240]); fx(bg, "ADBE Gaussian Blur 2", { "Blurriness": 45, "Repeat Edge Pixels": 1 });
    } else {
      bg = main.layers.addSolid(hex(col), "solid", main.width, main.height, 1); bg.startTime = 0;
    }
    bg.name = "infbg " + sh.name; bg.inPoint = sh.inPoint; bg.outPoint = sh.outPoint; bg.moveAfter(sh);
  }
}
