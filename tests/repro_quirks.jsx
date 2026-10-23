// Checks the EffectCraft JSX gotchas that can be verified without rendering.
// Run: effectcraft-cli script repro.jsx --empty
// PRESENT = the quirk still happens in your build. gone = fixed upstream; ignore that tip.

var results = [];
function check(name, present, detail) {
  results.push((present ? "PRESENT " : "gone    ") + name + (detail ? "  (" + detail + ")" : ""));
}

var c = app.project.items.addComp("gotchas", 1080, 1080, 1, 2, 20);

// 1. On a shape layer that already has a group, property("Position") keys the GROUP transform.
var s = c.layers.addShape();
var g = s.property("Contents").addProperty("ADBE Vector Group");
g.property("Contents").addProperty("ADBE Vector Shape - Rect");
s.property("Position").setValueAtTime(0, [100, 100]);
s.property("Position").setValueAtTime(1, [900, 900]);
var layerKeys = s.property("ADBE Transform Group").property("Position").numKeys;
var groupKeys = g.property("Transform").property("Position").numKeys;
check('shape layer: property("Position") keys the first group, not the layer',
      layerKeys == 0 && groupKeys > 0, "layer keys " + layerKeys + ", group keys " + groupKeys);

// 2. Two keyframes less than one frame apart collapse into one.
var t = c.layers.addSolid([1, 0, 0], "solid", 100, 100, 1);
var sc = t.property("ADBE Transform Group").property("Scale");
sc.setValueAtTime(1.0, [100, 100]);
sc.setValueAtTime(1.001, [115, 115]);
check("keys less than one frame apart merge", sc.numKeys < 2, "numKeys " + sc.numKeys);

writeLn(results.join("\n"));
