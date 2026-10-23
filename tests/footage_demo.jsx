// Builds comps exercising jsx/footage.jsx on clips tests/test_engine.py writes into the working directory:
// red/green/blue.mp4 (2 s solids), ramp.mp4 (4 s, grey level = 2 x frame number), tone.mp4 (4 s with a 440 Hz tone).
// Prints FOOT {...} lines with structural facts; the test renders frames and reads the pixels.
#include "../jsx/helpers.jsx"
#include "../jsx/footage.jsx"
W = 320; H = 240; FPS = 25;
var cwd = new File(".").fsName.replace(/\\/g, "/").replace(/\/\.?$/, "") + "/";
function v(n) { return cwd + n + ".mp4"; }
var facts = {};

var asm = comp("ASM", 4, "#000000");
assemble(asm, [{ file: v("red"), "in": 0, out: 1 }, { file: v("green"), "in": 0, out: 1 },
               { file: v("blue"), "in": 0, out: 1, transition: "crossfade", dur: 0.4 }]);

var rp = comp("RAMP", 4, "#000000"); var r1 = placeClip(rp, v("ramp"), 0, 4, 0);
speedRamp(r1, [[0, 1], [1, 2], [2, 0.5]]);
var fz = comp("FREEZE", 5, "#000000"); freezeFrame(placeClip(fz, v("ramp"), 0, 4, 0), 1.0, 1.0);
var rv = comp("REV", 2, "#000000"); reverseClip(placeClip(rv, v("ramp"), 0, 2, 0));
var sd = comp("SPEED", 2, "#000000"); var s1 = placeClip(sd, v("ramp"), 0, 2, 0); setSpeed(s1, 2); facts.speedOut = s1.outPoint;
var sl = comp("SLIP", 2, "#000000"); slip(placeClip(sl, v("ramp"), 0, 1, 0), 1.0);

var pp = comp("PIP", 2, "#000000"); placeClip(pp, v("red"), 0, 2, 0);
var g = placeClip(pp, v("green"), 0, 2, 0); pip(pp, g, [200, 20, 100, 80], { border: "#ffffff" });
var sp = comp("SPLIT", 2, "#000000");
splitScreen(sp, [placeClip(sp, v("red"), 0, 2, 0), placeClip(sp, v("blue"), 0, 2, 0)], "h2");

var lk = comp("LOOK", 2, "#000000"); var lc = placeClip(lk, v("ramp"), 0, 2, 0);
matchColor(lc, { levels: { Red: { "Input Black": 0, "Input White": 1, "Gamma": 1, "Output Black": 0, "Output White": 0.5 },
                           Green: { "Input Black": 0, "Input White": 1, "Gamma": 1, "Output Black": 0, "Output White": 1 },
                           Blue: { "Input Black": 0, "Input White": 1, "Gamma": 1, "Output Black": 0, "Output White": 1 } } });
look(lc, "teal-orange", 0.5); filmLook(lk, { bars: 30, flicker: false, weave: false });

var au = comp("AUD", 4, "#000000");
var a1 = placeClip(au, v("tone"), 0, 2, 0), b1 = placeClip(au, v("tone"), 2, 4, 2);
var jc = jCut(au, a1, b1, 0.5); facts.jcutIn = jc.inPoint; facts.jcutVideoOff = !jc.enabled; facts.bAudio = b1.audioEnabled;
var music = placeClip(au, v("tone"), 0, 4, 0); duck(music, [[1, 2]], -12, 0.25);
facts.duckAt15 = levels(music).valueAtTime(1.5, false)[0]; facts.duckAt3 = levels(music).valueAtTime(3, false)[0];
audioFade(a1, 0.3, 0.3); facts.fadeAt0 = levels(a1).valueAtTime(0, false)[0];

var pn = comp("PUNCH", 2, "#000000"); var pl = placeClip(pn, v("ramp"), 0, 2, 0); facts.punchBase = P(pl, "Scale").value[0];
punchIn(pl, 1.0, 130); facts.punchAt15 = P(pl, "Scale").valueAtTime(1.5, false)[0];
var tr = comp("TRANS", 3, "#000000");
assemble(tr, [{ file: v("red"), "in": 0, out: 1 }, { file: v("green"), "in": 0, out: 1, transition: "whip" },
              { file: v("blue"), "in": 0, out: 1, transition: "dip", dur: 0.2 }]);

fxCheck();
app.project.save(new File(cwd + "_footage.ecproj"));
writeLn("FOOT " + JSON.stringify(facts));
