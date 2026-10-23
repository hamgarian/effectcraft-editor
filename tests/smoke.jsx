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

// compositeCutout: plate, cast, contact, cut-out, shade + its alpha matte, wrap + its luma matte = 8 layers, mattes set
var plate = comp("plate", 2, "#506070"), cut = comp("cut", 2, null, 200, 400);
cut.layers.addSolid([0.9, 0.2, 0.2], "body", 120, 300, 1);
var cc = comp("composite", 2, null);
var kid = compositeCutout(cc, plate, cut, [540, 500]);
check(cc.numLayers == 8, "compositeCutout layers: got " + cc.numLayers);
var mattes = 0; for (var mi = 1; mi <= cc.numLayers; mi++) { try { if (cc.layer(mi).trackMatteType != TrackMatteType.NO_TRACK_MATTE) mattes++; } catch (e) {} }
check(mattes == 2, "compositeCutout track mattes: got " + mattes);
check(kid.property("Effects").numProperties == 4, "cut-out grade effects (hue/sat, levels, blur, noise): got " + kid.property("Effects").numProperties);

// mask, expression, captions
var ms = main.layers.addSolid([0, 0.5, 1], "masked", 200, 200, 1);
mask(ms, [[20, 20], [180, 20], [180, 180], [20, 180]], { feather: 10 });
check(ms.property("ADBE Mask Parade").numProperties == 1, "mask added");
check(expr(P(ms, "Rotation"), "time*90", 1) == 90, "expression evaluates");
var cl = captionTrack(main, [{ t0: 0.2, t1: 0.8, text: "hello" }, { t0: 1.0, t1: 1.6, text: "there" }], { box: "#000000" });
check(cl.property("Source Text").valueAtTime(0.5, false).text == "hello" && cl.property("Source Text").valueAtTime(0.9, false).text == " ", "caption timing");

// every effect used so far must have resolved; then a bogus name must be caught by fxCheck()
check(FX_FAILS.length == 0, "effect failures: " + FX_FAILS.join("; "));
fx(sl, "ADBE Hue/Saturation", {});
var caught = false; try { fxCheck(); } catch (e) { caught = true; }
check(caught, "fxCheck must throw on an unresolved effect name");

writeLn(fails.length ? "SMOKE FAIL: " + fails.join("; ") : "SMOKE OK");
