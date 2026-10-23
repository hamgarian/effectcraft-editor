// Core helpers for EffectCraft build scripts (tested on EffectCraft 0.14.0, `effectcraft-cli script X.jsx --empty`).
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

function fx(l, match, params) {
  var e = null, why = "";
  try { e = l.property("Effects").addProperty(match); } catch (err) { why = String(err); }
  if (!e) { log("effect failed: " + match + " on '" + l.name + "' " + why); return null; }
  for (var k in params) { try { e.property(k).setValue(params[k]); } catch (err) { log("fx param " + match + "/" + k + ": " + err); } }
  return e;
}

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
