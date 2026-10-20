(function () {
  var root = document.documentElement;
  // theme toggle (dark is the default look)
  var btn = document.getElementById("themebtn");
  if (btn) btn.addEventListener("click", function () {
    var cur = root.dataset.theme || "dark";
    var next = cur === "light" ? "dark" : "light";
    root.dataset.theme = next;
    try { localStorage.setItem("tm-theme", next); } catch (e) {}
  });

  // tabs: buttons with data-panel inside a .wtabs group toggle sibling panels
  document.querySelectorAll(".wtabs").forEach(function (group) {
    var btns = group.querySelectorAll(".wt");
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        btns.forEach(function (o) {
          o.classList.toggle("on", o === b);
          var p = document.getElementById(o.dataset.panel);
          if (p) p.hidden = o !== b;
        });
      });
    });
  });

  // latest-news filter chips
  var chips = document.getElementById("latestchips"), list = document.getElementById("latestlist");
  if (chips && list) chips.addEventListener("click", function (ev) {
    var b = ev.target.closest(".chipf"); if (!b) return;
    chips.querySelectorAll(".chipf").forEach(function (o) { o.classList.toggle("on", o === b); });
    var c = b.dataset.cat;
    list.querySelectorAll("li").forEach(function (li) { li.hidden = c !== "all" && li.dataset.cat !== c; });
  });

  // copy link buttons
  document.querySelectorAll(".copy").forEach(function (b) {
    b.addEventListener("click", function () {
      if (navigator.clipboard) navigator.clipboard.writeText(b.dataset.url).then(function () { b.textContent = "Link copied"; }).catch(function () {});
    });
  });

  // search
  var q = document.getElementById("q"), box = document.getElementById("qres"), idx = null, base = (document.querySelector(".brand") || {}).getAttribute ? document.querySelector(".brand").getAttribute("href") : "/";
  function load(cb) {
    if (idx) return cb();
    fetch(base + "search.json").then(function (r) { return r.json(); }).then(function (d) { idx = d; cb(); }).catch(function () { idx = []; cb(); });
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function run() {
    var term = q.value.trim().toLowerCase();
    if (term.length < 2) { box.hidden = true; return; }
    load(function () {
      var words = term.split(/\s+/);
      var hits = idx.filter(function (x) { var hay = (x.t + " " + x.k + " " + x.c).toLowerCase(); return words.every(function (w) { return hay.indexOf(w) >= 0; }); }).slice(0, 8);
      box.innerHTML = hits.length ? hits.map(function (x) { return '<a href="' + esc(x.u) + '"><b>' + esc(x.t) + "</b><small>" + esc(x.c) + " · " + esc(x.d) + "</small></a>"; }).join("")
        : '<p class="none">No stories match “' + esc(q.value) + "”.</p>";
      box.hidden = false;
    });
  }
  if (q && box) {
    var t; q.addEventListener("input", function () { clearTimeout(t); t = setTimeout(run, 120); });
    q.addEventListener("focus", function () { load(function () {}); });
    document.addEventListener("click", function (ev) { if (!ev.target.closest(".search")) box.hidden = true; });
    q.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { box.hidden = true; q.blur(); } });
  }
})();
