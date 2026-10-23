// Motion templates: each builds a comp from options and returns it. Needs jsx/helpers.jsx first (#include both,
// then bundle). Every template can expose named controls (essentialize) and be exported as an .ectemplate that
// `effectcraft-cli render --template T.ectemplate --values v.json` renders without a script.
// Timings follow the motion rules: snap entrances, one hold, quick exits; nothing fades that could cut.

// text layers sit on their baseline; centred text (the default) gets its anchor on the measured ink centre, so its
// Position IS its visual centre (left-aligned text keeps the baseline, which is what lower thirds line up on)
function text(c, str, o) {
  o = o || {};
  var l = c.layers.addText(str), sp = l.property("Source Text"), td = sp.value;
  td.font = o.font || "Arial Black"; td.fontSize = o.size || 80; td.applyFill = true; td.fillColor = hex(o.fill || "#ffffff");
  try { td.justification = o.left ? ParagraphJustification.LEFT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY; } catch (e) {}
  if (o.tracking) td.tracking = o.tracking;
  sp.setValue(td);
  if (!o.left) { try { var r = l.sourceRectAtTime(0, false); P(l, "Anchor Point").setValue([r.left + r.width / 2, r.top + r.height / 2]); } catch (e) {} }
  if (o.pos) P(l, "Position").setValue(o.pos);
  if (o.name) l.name = o.name;
  return l;
}

// a null to parent and scale/rotate things around: its anchor is reset to [0,0] because a null is a 100 px square
// anchored at [50,50], so children at [0,0] would sit 50 px up-left of the rig's position
function rig(c, name, pos, threeD) {
  var n = c.layers.addNull(); n.name = name; if (threeD) n.threeDLayer = true;
  P(n, "Anchor Point").setValue(threeD ? [0, 0, 0] : [0, 0]); P(n, "Position").setValue(pos);
  return n;
}

function rectLayer(c, name, size, pos, col, anchorLeft) {
  var l = c.layers.addShape(); l.name = name; P(l, "Position").setValue(pos);
  var g = shapeGroup(l, name), r = g.addProperty("ADBE Vector Shape - Rect");
  r.property("Size").setValue(size);
  if (anchorLeft) r.property("Position").setValue([size[0] / 2, 0]);   // grows from the left edge when scaled in X
  g.addProperty("ADBE Vector Graphic - Fill").property("Color").setValue(hex(col));
  return l;
}

// expose properties as named controls: [[layer, "text/sourceText" | "transform/opacity" | ..., "Control name"], ...]
function essentialize(c, controls) {
  var ids = [];
  for (var i = 0; i < controls.length; i++) {
    var r = app.run("essential.addProperty", { comp: c.name, layer: controls[i][0].name, path: controls[i][1], name: controls[i][2] });   // by name: give layers unique names
    if (r && r.controls) ids = ids.concat(r.controls);
  }
  return ids;
}
function exportTemplate(c, path) { return app.run("essential.exportTemplate", { comp: c.name, path: path, name: c.name }); }

// LOWER THIRD: accent bar wipes in from the left, name wipes on, role rises; reversed exit
function lowerThird(o) {
  o = o || {}; var w = o.w || W, h = o.h || H, d = o.dur || 4, x0 = o.x || w * 0.08, y0 = o.y || h * 0.78;
  var c = comp(o.comp || "Lower Third", d, null, w, h);
  var bar = rectLayer(c, "bar", [o.barW || w * 0.36, 8], [x0, y0 + 46], o.accent || "#e3982c", true);
  K(P(bar, "Scale"), [[0.1, [0, 100]], [0.4, [100, 100]], [d - 0.5, [100, 100]], [d - 0.25, [0, 100]]], "snap");
  var nm = text(c, o.name || "PIP ANDERSEN", { size: o.size || 54, fill: o.fill || "#ffffff", left: true, pos: [x0, y0], name: "name" });
  var wp = fx(nm, "Linear Wipe", { "Wipe Angle": 270, "Feather": 10 });
  if (wp) K(wp.property("Transition Completion"), [[0.15, 100], [0.55, 0], [d - 0.45, 0], [d - 0.2, 100]], "out");
  var rl = text(c, o.role || "night bus crew", { font: "Arial", size: (o.size || 54) * 0.5, fill: o.roleFill || "#d8d2c8", left: true, pos: [x0, y0 + 90], name: "role" });
  K(P(rl, "Position"), [[0.35, [x0, y0 + 110]], [0.7, [x0, y0 + 90]]], "out");
  K(P(rl, "Opacity"), [[0.35, 0], [0.6, 100], [d - 0.4, 100], [d - 0.2, 0]], "out");
  if (o.controls !== false) essentialize(c, [[nm, "text/sourceText", "Name"], [rl, "text/sourceText", "Role"]]);
  return c;
}

// TITLE CARD: background, title slams in with a 2-frame overshoot, subtitle rises, slow push the whole time
function titleCard(o) {
  o = o || {}; var w = o.w || W, h = o.h || H, d = o.dur || 3;
  var c = comp(o.comp || "Title Card", d, o.bg || "#101418", w, h);
  var rg = rig(c, "push", [w / 2, h / 2]);
  K(P(rg, "Scale"), [[0, [100, 100]], [d, [104, 104]]], "lin");
  var ts = o.size || w * 0.1, ss = ts * 0.28;
  var t = text(c, o.title || "NIGHT BUS", { size: ts, fill: o.fg || "#f2ece0", tracking: o.tracking || 40, name: "title" });
  t.parent = rg; P(t, "Position").setValue([0, -h * 0.02]);
  K(P(t, "Scale"), [[0.1, [0, 0]], [0.2, [112, 112]], [0.3, [100, 100]]], "snap");
  var s = text(c, o.sub || "a film by the crew", { font: "Arial", size: ss, fill: o.subFill || "#9aa0a8", name: "sub" });
  s.parent = rg; K(P(s, "Position"), [[0.35, [0, ts * 0.62 + ss * 1.2]], [0.75, [0, ts * 0.62 + ss * 0.6]]], "out");   // just under the title
  K(P(s, "Opacity"), [[0.35, 0], [0.7, 100]], "out");
  if (o.controls !== false) essentialize(c, [[t, "text/sourceText", "Title"], [s, "text/sourceText", "Subtitle"]]);
  return c;
}

// LOGO REVEAL: circle mask grows from the centre with a feathered edge, then a light sweep crosses the logo
// logo: a comp/footage item (keep it square-ish) or a string (rendered as text)
function logoReveal(o) {
  o = o || {}; var w = o.w || W, h = o.h || H, d = o.dur || 3;
  var c = comp(o.comp || "Logo Reveal", d, o.bg || "#0b0b0b", w, h);
  var lg = typeof o.logo == "object" ? c.layers.add(o.logo) : text(c, o.logo || "PIP", { size: w * 0.16, fill: o.fg || "#f2ece0", name: "logo" });
  var lgY = h / 2;
  P(lg, "Position").setValue([w / 2, lgY]); lg.name = "logo";
  var m = lg.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
  function circle(r) { var s = new Shape(), k = 0.5523 * r; s.vertices = [[0, -r], [r, 0], [0, r], [-r, 0]];
    s.inTangents = [[-k, 0], [0, -k], [k, 0], [0, k]]; s.outTangents = [[k, 0], [0, k], [-k, 0], [0, -k]]; s.closed = true; return s; }
  var mp = m.property("ADBE Mask Shape"), rmax = Math.max(w, h);
  mp.setValueAtTime(0.1, circle(1)); mp.setValueAtTime(0.8, circle(rmax)); m.property("ADBE Mask Feather").setValue([60, 60]);
  K(P(lg, "Scale"), [[0.1, [92, 92]], [1.2, [100, 100]], [d, [103, 103]]], "out");
  var sw = rectLayer(c, "sweep", [w * 0.06, h * 1.6], [w * 0.1, h / 2], "#ffffff");
  P(sw, "Rotation").setValue(20); sw.blendingMode = BlendingMode.ADD; P(sw, "Opacity").setValue(55);
  fx(sw, "Gaussian Blur", { "Blurriness": 30 });
  K(P(sw, "Position"), [[0.9, [w * 0.15, h / 2]], [1.6, [w * 0.85, h / 2]]], "in");
  var lgm = typeof o.logo == "object" ? c.layers.add(o.logo) : text(c, o.logo || "PIP", { size: w * 0.16, name: "logo matte" });
  P(lgm, "Position").setValue([w / 2, lgY]); sw.moveToBeginning(); lgm.moveToBeginning(); sw.trackMatteType = TrackMatteType.ALPHA;
  if (o.controls !== false && typeof o.logo != "object") essentialize(c, [[lg, "text/sourceText", "Logo text"]]);
  return c;
}

// KINETIC TYPE: one word at a time, each slamming in on its time (use beat times from scripts/audio.py beats)
function kineticType(o) {
  o = o || {}; var w = o.w || W, h = o.h || H, words = o.words || ["STACK", "'EM", "UP", "HIGH"];
  var times = o.times || (function () { var t = []; for (var i = 0; i < words.length; i++) t.push(0.1 + i * 0.43); return t; })();
  var d = o.dur || times[times.length - 1] + 1.0;
  var c = comp(o.comp || "Kinetic Type", d, o.bg || "#e9e5df", w, h);
  var rg = rig(c, "push", [w / 2, h / 2]);
  K(P(rg, "Scale"), [[0, [100, 100]], [d, [110, 110]]], "lin");
  for (var i = 0; i < words.length; i++) {
    var l = text(c, words[i], { size: o.size || w * 0.14, fill: i % 2 ? (o.accent || "#c8372a") : (o.fg || "#101418"), name: "word " + i });
    l.parent = rg; P(l, "Position").setValue([0, 0]); P(l, "Rotation").setValue(i % 2 ? 4 : -4);
    var t0 = times[i], t1 = i + 1 < times.length ? times[i + 1] : d;
    K(P(l, "Scale"), [[t0, [150, 150]], [t0 + 2 / FPS, [96, 96]], [t0 + 3 / FPS, [100, 100]]], "snap");
    K(P(l, "Opacity"), [[0, 0], [t0, 100], [t1, i + 1 < times.length ? 0 : 100]], "hold");
  }
  return c;
}

// 3D TEXT ORBIT: characters on a ring that turns once; 3D layers, default camera
function textOrbit3D(o) {
  o = o || {}; var w = o.w || W, h = o.h || H, d = o.dur || 4, str = o.text || "NIGHT BUS * ", r = o.radius || w * 0.3;
  var c = comp(o.comp || "Text Orbit", d, o.bg || "#06161c", w, h);
  var ring = rig(c, "ring", [w / 2, h / 2, 0], true);
  K(P(ring, "Y Rotation"), [[0, 0], [d, -360]], "lin"); P(ring, "X Rotation").setValue(o.tilt || -12);
  for (var i = 0; i < str.length; i++) {
    if (str.charAt(i) == " ") continue;
    var a = i / str.length * 2 * Math.PI, l = text(c, str.charAt(i), { size: o.size || w * 0.07, fill: o.fg || "#ebe4e2", name: "ch " + i });
    l.threeDLayer = true; l.parent = ring;
    P(l, "Position").setValue([Math.sin(a) * r, 0, -Math.cos(a) * r]); P(l, "Y Rotation").setValue(-a * 180 / Math.PI);
  }
  return c;
}

// SOCIAL REFRAME: put a comp into another format (9:16 / 1:1 / 4:5) over a blurred, enlarged copy of itself;
// `safe` draws the UI-safe area as a guide layer (turn it off before export)
var FORMATS = { landscape: [1920, 1080], vertical: [1080, 1920], square: [1080, 1080], portrait: [1080, 1350], classic: [1440, 1080] };
// commonly used margins for vertical feeds (platform UI covers them); check the platform before relying on them
var SAFE = { vertical: { top: 220, bottom: 420, left: 60, right: 140 }, square: { top: 60, bottom: 120, left: 60, right: 60 },
             portrait: { top: 80, bottom: 220, left: 60, right: 60 }, landscape: { top: 54, bottom: 54, left: 96, right: 96 } };
function socialReframe(inner, preset, o) {
  o = o || {}; var f = FORMATS[preset] || FORMATS.vertical, s = SAFE[preset] || SAFE.vertical;
  var c = comp(o.comp || (inner.name + " " + preset), inner.duration, "#000000", f[0], f[1]);
  var bg = c.layers.add(inner), k = Math.max(f[0] / inner.width, f[1] / inner.height) * 100 * 1.15;
  P(bg, "Position").setValue([f[0] / 2, f[1] / 2]); P(bg, "Scale").setValue([k, k]); bg.name = "fill blur";
  fx(bg, "Gaussian Blur", { "Blurriness": 60, "Repeat Edge Pixels": 1 }); fx(bg, "ADBE Easy Levels2", { "Output White": 0.6 });
  var fg = c.layers.add(inner), fit = Math.min((f[0] - s.left - s.right) / inner.width, (f[1] - s.top - s.bottom) / inner.height) * 100;
  P(fg, "Position").setValue([(s.left + f[0] - s.right) / 2, (s.top + f[1] - s.bottom) / 2]); P(fg, "Scale").setValue([fit, fit]); fg.name = "content";
  if (o.safe) {
    var g = c.layers.addShape(); g.name = "SAFE GUIDE (disable before export)"; try { g.guideLayer = true; } catch (e) {}
    var gg = shapeGroup(g, "safe"), rr2 = gg.addProperty("ADBE Vector Shape - Rect");
    rr2.property("Size").setValue([f[0] - s.left - s.right, f[1] - s.top - s.bottom]);
    gg.addProperty("ADBE Vector Graphic - Stroke").property("Color").setValue([1, 0, 1]);
    P(g, "Position").setValue([(s.left + f[0] - s.right) / 2, (s.top + f[1] - s.bottom) / 2]);
  }
  return c;
}
