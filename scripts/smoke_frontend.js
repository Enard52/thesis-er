/* Smoke test for site/app.js new behavior (tickets 07-12): run with `node scripts/smoke_frontend.js`.
   Stubs just enough DOM for app.js load + renderReport, then asserts the
   generated links, counts, and rules-tab rendering. */
"use strict";
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const SITE = path.join(__dirname, "..", "site");
const failures = [];
let scrollCalls = 0;
function assert(cond, msg) { if (!cond) failures.push(msg); }

function makeEl(tag) {
  const listeners = {};
  const classes = new Set();
  const attrs = {};
  const el = {
    tag, children: [], innerHTML: "", textContent: "", value: "purdue",
    hidden: false, disabled: false, href: "",
    classList: {
      toggle(c, force) { if (force === undefined) { classes.has(c) ? classes.delete(c) : classes.add(c); } else if (force) classes.add(c); else classes.delete(c); },
      add(c) { classes.add(c); },
      remove(c) { classes.delete(c); },
      contains(c) { return classes.has(c); },
    },
    style: {},
    appendChild(c) { this.children.push(c); return c; },
    addEventListener(ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
    fire(ev, arg) { (listeners[ev] || []).forEach((fn) => fn(arg)); },
    setAttribute(k, v) { attrs[k] = String(v); },
    removeAttribute(k) { delete attrs[k]; },
    getAttribute(k) { return k in attrs ? attrs[k] : null; },
    getBoundingClientRect: () => ({ top: 100 }),
    scrollIntoView() { scrollCalls += 1; },
    click() {},
    remove() {},
  };
  return el;
}

const byId = {};
["uni", "file", "dropzone", "dz-status", "queue", "q-name", "q-size", "go",
 "progress", "progress-bar", "status", "form-error", "results", "verdict",
 "summary", "ada", "formatting", "repo-cta", "repo-link", "copy-report",
 "download-json", "q-remove", "rules-list", "rules-feedback", "report-wrong",
 "request-school", "stage", "checker", "rules", "how", "universities", "about", "hero",
].forEach((id) => { byId[id] = makeEl("div"); });
byId["hero"].offsetHeight = 700;

const navLinks = ["checker", "rules", "how", "universities", "about"].map((id) => {
  const a = makeEl("a");
  a.setAttribute("href", "#" + id);
  return a;
});
const ctaLinks = ["checker", "rules"].map((id) => {
  const a = makeEl("a");
  a.setAttribute("href", "#" + id);
  return a;
});

const countSpans = [makeEl("span"), makeEl("span"), makeEl("span")];
const repoFileAnchors = [makeEl("a"), makeEl("a"), makeEl("a")];
repoFileAnchors[0].getAttribute = () => "RULES.md";
repoFileAnchors[1].getAttribute = () => "README.md";
repoFileAnchors[2].getAttribute = () => "CONTRIBUTING.md";
const requestSchool = byId["request-school"];

const documentStub = {
  getElementById: (id) => byId[id] || makeEl("div"),
  querySelectorAll: (sel) => {
    if (sel === "[data-rule-count]") return countSpans;
    if (sel === "[data-repo-file]") return repoFileAnchors;
    if (sel === "#nav-links a") return navLinks;
    if (sel === "#nav-links a, .cta-row a") return navLinks.concat(ctaLinks);
    return [];
  },
  querySelector: (sel) => sel === ".hero" ? byId["hero"] : null,
  createElement: (tag) => makeEl(tag),
  addEventListener: () => {},
  body: makeEl("body"),
  documentElement: makeEl("html"),
};
documentStub.documentElement.scrollHeight = 2400;
documentStub.documentElement.style.setProperty = function (k, v) { this[k] = v; };

const winListeners = {};
const sandbox = {
  console, location: { href: "https://mogiiee.github.io/thesis-er/", hash: "" },
  history: { replaceState: () => {} },
  document: documentStub,
  navigator: {},
  matchMedia: () => ({ matches: false }),
  scrollY: 0, pageYOffset: 0, innerHeight: 800,
  requestAnimationFrame: (fn) => fn(),
  addEventListener: (ev, fn) => { (winListeners[ev] = winListeners[ev] || []).push(fn); },
  fetch: () => ({ then: () => ({ then: () => ({ catch: () => {} }) }) }),
  FormData: function () { this.append = () => {}; },
  FileReader: function () {},
  Blob: undefined, URL: undefined,
  window: {},
};
sandbox.window = sandbox;
vm.createContext(sandbox);
for (const f of ["config.js", "rules.js", "app.js"]) {
  vm.runInContext(fs.readFileSync(path.join(SITE, f), "utf8"), sandbox, { filename: f });
}

// 1. counts stamped everywhere from the generator
const RULE_COUNT = vm.runInContext("RULE_COUNT", sandbox);
const RULE_FAMILIES = vm.runInContext("RULE_FAMILIES", sandbox);
const renderReport = vm.runInContext("window.renderReport", sandbox);
assert(RULE_COUNT === 89, `RULE_COUNT is ${RULE_COUNT}, want 89`);
countSpans.forEach((el, i) => assert(el.textContent === 89, `count span ${i} = ${el.textContent}`));

// 2. repo-file links resolve to real blob URLs
const REPO = "https://github.com/mogiiee/thesis-er";
repoFileAnchors.forEach((a, i) => assert(
  a.href.startsWith(REPO + "/blob/main/") && a.target === "_blank",
  `repo-file anchor ${i} href = ${a.href}`));

// 3. request-school + rules feedback point at the right templates
assert(documentStub.getElementById("request-school").href ===
  REPO + "/issues/new?template=university-request.md", "request-school link");
assert(byId["rules-feedback"].innerHTML.includes("template=rule-correction.md"),
  "rules feedback links rule-correction template");

// 4. rules tab rendered every family and every rule exactly once
const families = RULE_FAMILIES;
const rendered = byId["rules-list"].children;
assert(rendered.length === families.length,
  `rendered ${rendered.length} families, want ${families.length}`);
const total = families.reduce((n, f) => n + f.rules.length, 0);
assert(total === 89, `catalog holds ${total} rules, want 89`);

// 5. a report wires the pre-filled "looks wrong" link
renderReport({
  verdict: "FAIL", filename: "my thesis.docx", errors: 2, infos: 1,
  university: "purdue", ada: [],
  formatting: [{ rule: "H1.8.FONT", severity: "ERROR",
                 items: [{ loc: "p.3", msg: "uses Calibri" }] }],
});
const wrong = byId["report-wrong"].href;
assert(wrong.includes("template=rule-correction.md") && wrong.includes("my%20thesis.docx"),
  `report-wrong href = ${wrong}`);
assert(byId["verdict"].textContent.includes("FAIL"), "verdict rendered");
assert(byId["results"].hidden === false, "report is visible on checker card");

// 6. tab deck: one card forward, rest floating behind, hash-driven
const activateCard = vm.runInContext("window.activateCard", sandbox);
assert(typeof activateCard === "function", "activateCard exposed");
assert(byId["checker"].classList.contains("active"), "checker active on load");
assert(byId["rules"].classList.contains("background"), "rules in background on load");
assert(byId["rules"].getAttribute("inert") === "", "background card is inert");
activateCard("rules");
assert(byId["rules"].classList.contains("active"), "rules comes forward");
assert(byId["results"].hidden === true, "report leaves flow on non-checker card");
assert(byId["checker"].classList.contains("background"), "checker recedes");
assert(byId["checker"].getAttribute("inert") === "", "receded card is inert");
assert(byId["rules"].getAttribute("inert") === null, "forward card is interactive");
assert(navLinks[1].getAttribute("aria-current") === "page", "nav marks current tab");
assert(navLinks[0].getAttribute("aria-current") === null, "nav unmarks old tab");
activateCard("bogus");
assert(byId["checker"].classList.contains("active"), "unknown hash falls back to checker");
assert(byId["results"].hidden === false, "existing report returns with checker card");
// nav click interception
let prevented = false;
navLinks[1].fire("click", { preventDefault: () => { prevented = true; } });
assert(prevented && byId["rules"].classList.contains("active"), "nav click switches tab");
assert(scrollCalls > 0, "tab navigation scrolls the 3D stage into view");

// 7. scroll choreography writes bounded CSS progress variables
sandbox.scrollY = 350;
(winListeners.scroll || []).forEach((fn) => fn());
assert(documentStub.documentElement.style["--hero-progress"] === "0.6410",
  `hero scroll progress = ${documentStub.documentElement.style["--hero-progress"]}`);
assert(documentStub.documentElement.style["--page-progress"] === "0.2188",
  `page scroll progress = ${documentStub.documentElement.style["--page-progress"]}`);

if (failures.length) {
  console.error("SMOKE FAIL:");
  failures.forEach((f) => console.error("  - " + f));
  process.exit(1);
}
console.log(`smoke_frontend: OK (${families.length} families, ${total} rules, all links wired)`);
