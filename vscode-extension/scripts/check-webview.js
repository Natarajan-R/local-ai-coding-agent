// Guard: the webview script lives inside a TS template literal, where an escape like
// \n silently becomes a real newline and breaks the emitted JS -- the panel then shows
// nothing and hangs on "Connecting...", while the socket connects fine. Parse what the
// webview would actually receive, so that can never ship again.
// Load extension.js with a stubbed 'vscode' module, render getHtml(), and
// syntax-check the <script> the webview would actually receive.
const Module = require('module');
const path = require('path');
const vm = require('vm');
const orig = Module._load;
Module._load = function (req, parent, isMain) {
  if (req === 'vscode') {
    return { window: { createOutputChannel: () => ({ appendLine(){}, dispose(){} }) },
             commands: { registerCommand: () => ({}) },
             workspace: { getConfiguration: () => ({ get: (k, d) => d }) },
             ViewColumn: { Beside: 2 } };
  }
  return orig.apply(this, arguments);
};
const file = path.resolve(process.argv[2]);
const src = require('fs').readFileSync(file, 'utf8');
// getHtml is module-private; expose it by evaluating the module and grabbing it.
const sandboxExports = {};
const m = { exports: sandboxExports };
const fn = new Function('exports', 'require', 'module', '__filename', '__dirname',
                        src + '\n;module.exports.__getHtml = typeof getHtml !== "undefined" ? getHtml : null;');
fn(m.exports, Module.createRequire(file), m, file, path.dirname(file));
const getHtml = m.exports.__getHtml;
if (!getHtml) { console.error('could not reach getHtml'); process.exit(2); }
const html = getHtml({ cspSource: 'x' });
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) { console.error('no <script> found'); process.exit(2); }
let bad = 0;
scripts.forEach((s, i) => {
  try { new vm.Script(s); console.log(`script #${i + 1}: OK (${s.split('\n').length} lines parse cleanly)`); }
  catch (e) { bad++; console.error(`script #${i + 1}: SYNTAX ERROR -> ${e.message}`); }
});
process.exit(bad ? 1 : 0);
