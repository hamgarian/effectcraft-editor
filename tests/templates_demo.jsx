// Builds every template into _templates.ecproj (in the working directory) and exports the lower third as an
// .ectemplate. tests/test_engine.py runs it, renders a frame of each comp and renders the template with new values.
#include "../jsx/helpers.jsx"
#include "../jsx/templates.jsx"
W = 1280; H = 720; FPS = 25;
var made = [lowerThird({ comp: "LT" }), titleCard({ comp: "TC" }), logoReveal({ comp: "LR" }),
            kineticType({ comp: "KT" }), textOrbit3D({ comp: "OR" })];
made.push(socialReframe(made[1], "vertical", { comp: "TC vertical", safe: true }));
var cwd = new File(".").fsName.replace(/\\/g, "/").replace(/\/\.?$/, "");
var tr = exportTemplate(made[0], cwd + "/_lower_third.ectemplate");
fxCheck();
app.project.save(new File(cwd + "/_templates.ecproj"));
writeLn("TEMPLATES OK " + made.length + " comps; template " + JSON.stringify(tr).slice(0, 80));
