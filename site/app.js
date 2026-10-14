/* global REPO_URL, BACKEND_URL */
(function () {
  "use strict";
  var MAX_BYTES = 50 * 1024 * 1024;
  var API = (typeof BACKEND_URL !== "undefined" && BACKEND_URL) || "";
  var uniSel = document.getElementById("uni");
  var fileInput = document.getElementById("file");
  var dropzone = document.getElementById("dropzone");
  var dzStatus = document.getElementById("dz-status");
  var queueEl = document.getElementById("queue");
  var qName = document.getElementById("q-name");
  var qSize = document.getElementById("q-size");
  var goBtn = document.getElementById("go");
  var progressEl = document.getElementById("progress");
  var progressBar = document.getElementById("progress-bar");
  var statusEl = document.getElementById("status");
  var formError = document.getElementById("form-error");
  var resultsEl = document.getElementById("results");
  var currentFile = null;
  var lastReport = null;

  fetch(API + "api/universities").then(function (r) { return r.json(); }).then(function (data) {
    uniSel.innerHTML = "";
    (data.universities || ["purdue"]).forEach(function (u) {
      var o = document.createElement("option");
      o.value = u; o.textContent = u.charAt(0).toUpperCase() + u.slice(1);
      uniSel.appendChild(o);
    });
  }).catch(function () { /* default option stays */ });

  if (typeof REPO_URL !== "undefined" && REPO_URL) {
    document.getElementById("repo-cta").innerHTML =
      'If this saved you a rejected submission, please <a href="' + REPO_URL + '">star the repo</a> — pull requests welcome, Hacktoberfest-friendly.';
    document.getElementById("repo-link").innerHTML = '<a href="' + REPO_URL + '">GitHub</a>';
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function fmtSize(n) {
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    return (n / 1048576).toFixed(1) + " MB";
  }

  function say(msg, isError) {
    dzStatus.textContent = msg;
    dropzone.classList.toggle("invalid", !!isError);
  }

  function showError(msg) {
    formError.textContent = msg;
    formError.hidden = false;
  }

  function clearError() {
    formError.hidden = true;
    formError.textContent = "";
  }

  /* One path for picker and dropped files, with up-front validation. */
  function takeFile(f) {
    clearError();
    dropzone.classList.remove("invalid");
    if (!f) return;
    if (!/\.docx$/i.test(f.name)) {
      say("That’s not a Word file — choose a .docx.", true);
      return;
    }
    if (f.size > MAX_BYTES) {
      say("That file is " + fmtSize(f.size) + " — the limit is 50 MB.", true);
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      var bytes = new Uint8Array(reader.result);
      if (!(bytes[0] === 0x50 && bytes[1] === 0x4b)) {
        say("That file isn’t really a .docx (renamed?) — pick the Word export.", true);
        return;
      }
      currentFile = f;
      qName.textContent = f.name;
      qSize.textContent = fmtSize(f.size) + " · ready to check";
      queueEl.hidden = false;
      progressEl.hidden = true;
      say(f.name + " added — press “Run the 85 checks”.", false);
    };
    reader.readAsArrayBuffer(f.slice(0, 2));
  }

  fileInput.addEventListener("change", function () { takeFile(fileInput.files[0]); });
  document.getElementById("q-remove").addEventListener("click", function () {
    currentFile = null;
    fileInput.value = "";
    queueEl.hidden = true;
    say("", false);
  });

  ["dragenter", "dragover"].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault();
      var kinds = (e.dataTransfer && e.dataTransfer.types) || [];
      var hasFiles = Array.prototype.indexOf.call(kinds, "Files") !== -1;
      dropzone.classList.toggle("dragover", hasFiles);
      if (!hasFiles) say("Only files can be dropped here.", true);
    });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (ev === "drop" && e.dataTransfer && e.dataTransfer.files.length) takeFile(e.dataTransfer.files[0]);
    });
  });
  /* Never let a stray drop navigate the page away. */
  ["dragover", "drop"].forEach(function (ev) {
    document.addEventListener(ev, function (e) { e.preventDefault(); });
  });

  function renderGroups(el, groups) {
    el.innerHTML = "";
    if (!groups.length) {
      var p = document.createElement("p");
      p.className = "empty"; p.textContent = "No issues found in this section.";
      el.appendChild(p);
      return;
    }
    groups.forEach(function (g) {
      var d = document.createElement("details");
      d.className = "rule";
      if (g.severity === "ERROR") d.open = true;
      var items = g.items.map(function (it) {
        return "<li><code class=\"loc\">" + esc(it.loc) + "</code> — " + esc(it.msg) + "</li>";
      }).join("");
      d.innerHTML = "<summary><span class=\"sev " + g.severity + "\">" + g.severity + "</span>" +
        esc(g.rule) + " (" + g.items.length + ")</summary><ul>" + items + "</ul>";
      el.appendChild(d);
    });
  }

  function renderReport(report) {
    lastReport = report;
    var verdictEl = document.getElementById("verdict");
    verdictEl.textContent = (report.verdict === "PASS" ? "✓ PASS" : "✗ FAIL") + " — " + report.filename;
    verdictEl.className = report.verdict === "PASS" ? "pass" : "fail";
    resultsEl.classList.toggle("verdict-pass", report.verdict === "PASS");
    resultsEl.classList.toggle("verdict-fail", report.verdict !== "PASS");
    document.getElementById("summary").textContent =
      report.errors + " error(s), " + report.infos + " info note(s) against the " +
      report.university + " rules." +
      (report.verdict === "PASS"
        ? " Nothing here would fail you — still confirm against the official handbook before submitting."
        : " Start with the ERROR items: each one says what the handbook wants instead.");
    renderGroups(document.getElementById("ada"), report.ada);
    renderGroups(document.getElementById("formatting"), report.formatting);
    resultsEl.hidden = false;
    resultsEl.scrollIntoView();
  }

  goBtn.addEventListener("click", function () {
    if (!currentFile) { showError("Choose a .docx file first."); return; }
    clearError();
    goBtn.disabled = true;
    progressEl.hidden = false;
    progressBar.setAttribute("aria-valuenow", "50");
    statusEl.textContent = "Reading styles, figures, and images… large theses can take a minute. Your file never leaves this analysis.";
    var fd = new FormData();
    fd.append("file", currentFile);
    fd.append("university", uniSel.value);
    fetch(API + "api/check", { method: "POST", body: fd }).then(function (r) {
      return r.json().then(function (body) { return { ok: r.ok, body: body }; });
    }).then(function (res) {
      goBtn.disabled = false;
      progressEl.hidden = true;
      if (!res.ok) { showError("Could not analyze that file: " + (res.body.error || "unknown error")); return; }
      statusEl.textContent = "";
      renderReport(res.body);
    }).catch(function (e) {
      goBtn.disabled = false;
      progressEl.hidden = true;
      showError(API ? "Something went wrong talking to the checker: " + e.message
        : "The live analyzer isn't deployed on this page yet — clone the repo and run the checker on your own machine instead (README, one command; works fully offline).");
    });
  });

  document.getElementById("copy-report").addEventListener("click", function () {
    if (!lastReport || !navigator.clipboard) return;
    var lines = [(lastReport.verdict + " — " + lastReport.filename),
      lastReport.errors + " error(s), " + lastReport.infos + " info note(s)"];
    lastReport.ada.concat(lastReport.formatting).forEach(function (g) {
      lines.push(g.severity + " " + g.rule + " (" + g.items.length + ")");
      g.items.forEach(function (it) { lines.push("  " + it.loc + ": " + it.msg); });
    });
    navigator.clipboard.writeText(lines.join("\n"));
    statusEl.textContent = "Summary copied to clipboard.";
  });

  document.getElementById("download-json").addEventListener("click", function () {
    if (!lastReport || typeof Blob === "undefined" || typeof URL === "undefined") return;
    var blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "format-report.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  /* exposed for automated verification */
  window.renderReport = renderReport;
})();
