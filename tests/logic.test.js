// Checks the timeline maths and the honesty of its wording.
// Run: node tests/logic.test.js   (no dependencies)
const fs = require("fs"), vm = require("vm"), path = require("path"), assert = require("assert");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

// Pull the small pure helpers out of index.html and run them in a sandbox.
const grab = re => { const m = html.match(re); if (!m) throw new Error("missing " + re); return m[0]; };
const code = [
  grab(/const ym=s=>[^\n]*/), grab(/const months=[^\n]*/), grab(/const fmtYM=[^\n]*/),
  grab(/function stats\(p\)\{[\s\S]*?\n\}/), grab(/function stageFor\(p\)[^\n]*/),
  grab(/const PCT_WORDS=[^\n]*/), grab(/const pctShort=[^\n]*/), grab(/const dateLabel=[^\n]*/), grab(/const srcName=[^\n]*/),
  grab(/function verdict\(p,k\)\{[\s\S]*?\n\}/),
  grab(/function metres\(a,b\)[^\n]*/), grab(/function busiest\(\)\{[\s\S]*?return best\}/),
].join("\n");
const ctx = { P: [] }; vm.createContext(ctx); vm.runInContext(code + "\nthis.api={stats,verdict,stageFor,PCT_WORDS,pctShort,busiest};", ctx);
const { stats, verdict, stageFor, PCT_WORDS, pctShort, busiest } = ctx.api;

const ymOff = m => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() + m); return d.toISOString().slice(0, 7); };
const bto = (launch, ecd, delayed = "") => ({ kind: "BTO", name: "Test", launch, ecd, delayed, remark: delayed ? "Covid19: May delay up to 6 months(s) 2027-01-01" : "" });
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok -", name); };

t("percentage is time elapsed, clamped 0-100", () => {
  assert.ok(Math.abs(stats(bto(ymOff(-12), ymOff(12))).pct - 50) < 3);
  assert.strictEqual(stats(bto(ymOff(-48), ymOff(-2))).pct, 100);
  assert.strictEqual(stats(bto(ymOff(2), ymOff(40))).pct, 0);
  assert.strictEqual(stats(bto("", ymOff(40))).pct, null);
});
t("announced delay moves the estimated date", () => {
  const k = stats(bto(ymOff(-24), ymOff(0), ymOff(6)));
  assert.ok(k.pct < 100 && k.delay === 6);
  assert.match(verdict(bto(ymOff(-24), ymOff(0), ymOff(6)), k).t, /Delay announced/);
});
t("estimated date passing never claims completion or keys", () => {
  for (const p of [bto(ymOff(-50), ymOff(-1)), { ...bto(ymOff(-50), ymOff(-1)), kind: "Condo" }]) {
    const v = verdict(p, stats(p)), text = (v.t + " " + v.d).toLowerCase().replace(/we have no confirmation[^.]*\./, "");
    assert.match(v.t, /Estimated date reached/);
    assert.match(v.d, /no confirmation/);
    assert.doesNotMatch(text, /due now|is complete|completed|ready|keys are ready/);
  }
  assert.strictEqual(stageFor(100), "Estimated date reached");
});
t("wording says estimated timeline, not progress", () => {
  assert.strictEqual(PCT_WORDS, "of estimated timeline elapsed");
  assert.doesNotMatch(html, /of the wait to keys is over|Due now|>Pace</);
});
t("not-launched projects show no percentage", () => {
  assert.strictEqual(pctShort(stats(bto("", ymOff(30)))), "Not launched");
});
t("first visit lands on the busiest cluster", () => {
  ctx.P = [{ ll: [1.30, 103.70] }, { ll: [1.301, 103.701] }, { ll: [1.302, 103.702] }, { ll: [1.40, 103.90] }];
  vm.runInContext("P=this.P", ctx);
  assert.deepStrictEqual(busiest().ll.slice(0, 1), [1.30]);
});
t("map sprites and sheet art never draw a finished building from dates alone", () => {
  assert.ok((html.match(/done=false/g) || []).length >= 2);
});
console.log(`\n${n} checks passed`);
