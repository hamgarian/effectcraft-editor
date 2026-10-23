// Smoke test for jsx/helpers.jsx on a real EffectCraft. Run: python scripts/bundle.py tests/smoke.jsx _smoke.jsx
// then: effectcraft-cli script _smoke.jsx --empty   -> must print "SMOKE OK"
#include "../jsx/helpers.jsx"

var fails = [];
function check(ok, what) { if (!ok) fails.push(what); }

var main = comp("Main", 2, "#101820");
var shot = comp("ShotA", 2, "#ff0000");
var l = place(main, shot, 0.5, 1.5);
l.name = "ShotA";
check(Math.abs(l.inPoint - 0.5) < 1e-6 && Math.abs(l.outPoint - 1.5) < 1e-6, "place in/out");

// shape layer: P() must key the layer transform, not the first group's
var sl = main.layers.addShape(); sl.name = "shape";
var gc = shapeGroup(sl, "box");
var r = gc.addProperty("ADBE Vector Shape - Rect"); r.property("Size").setValue([100, 100]);
var st = gc.addProperty("ADBE Vector Graphic - Stroke");
dashes(st, 30, 10);
K(P(sl, "Position"), [[0, [100, 100]], [1, [500, 500]]], "snap");
check(P(sl, "Position").numKeys == 2, "layer position keys");
check(sl.property("Contents").property(1).property("Transform").property("Position").numKeys == 0, "group transform untouched");

// overlay must not get an infinite-background solid
var fl = place(main, comp("flash", 2, "#ffffff"), 0.9, 1.0); fl.name = "flash"; fl.blendingMode = BlendingMode.ADD;
var before = main.numLayers;
infiniteBackground(main, { ShotA: "#ff0000", flash: "#000000" });
check(main.numLayers == before + 1, "one fill (shot only, not overlay): got " + (main.numLayers - before));

writeLn(fails.length ? "SMOKE FAIL: " + fails.join("; ") : "SMOKE OK");
