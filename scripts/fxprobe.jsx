// Do these effect names resolve in this EffectCraft, to which match name, and with which parameter names?
// Find candidates first with:  effectcraft-cli exec effect.list --params "{\"filter\":\"hue\"}"
// addProperty() accepts the display name ("Hue/Saturation"), the id ("ec.color.huesaturation") or the AE match
// name ("ADBE HUE SATURATION"); a hybrid ("ADBE Hue/Saturation") resolves to nothing and fx() then fails silently.
// Edit NAMES, then: effectcraft-cli script scripts/fxprobe.jsx --empty
var NAMES = ["Hue/Saturation", "ADBE Hue/Saturation", "Color Balance", "Photo Filter", "Minimax", "Matte Choker", "Glow",
             "Light Wrap", "CC Light Wrap", "Set Matte"];
var c = app.project.items.addComp("probe", 100, 100, 1, 1, 20);
var l = c.layers.addSolid([1, 1, 1], "s", 100, 100, 1);
for (var i = 0; i < NAMES.length; i++) {
  var e = null;
  try { e = l.property("ADBE Effect Parade").addProperty(NAMES[i]); } catch (x) {}
  if (!e) { $.writeln("NO   " + NAMES[i]); continue; }
  var ps = []; for (var k = 1; k <= e.numProperties; k++) ps.push(e.property(k).name);
  $.writeln("YES  " + NAMES[i] + " = " + e.matchName + " -> " + ps.slice(0, 10).join(" | ") + (ps.length > 10 ? " | ..." : ""));
}
