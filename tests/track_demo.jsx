// tests/test_engine.py writes dot.mp4 (a marked square moving right) next to this bundle's working directory,
// runs this, and checks the title follows the square: prints "TRACK x0,y0 x1,y1"
#include "../jsx/helpers.jsx"
var cwd = new File(".").fsName.replace(/\\/g, "/").replace(/\/\.?$/, "");
var f = app.project.importFile(new ImportOptions(new File(cwd + "/dot.mp4")));
var c = app.project.items.addComp("T", 320, 240, 1, 2, 25);
var v = c.layers.add(f), title = c.layers.addText("TAG");
trackAttach(v, title, [60, 120]);
fxCheck();
var p = P(title, "Position");
writeLn("TRACK " + p.valueAtTime(0, false).slice(0, 2).join(",") + " " + p.valueAtTime(1.6, false).slice(0, 2).join(","));
