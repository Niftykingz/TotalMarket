(function () {
  var root = document.documentElement;
  // theme toggle (light is the default look; dark is optional)
  var btn = document.getElementById("themebtn");
  if (btn) btn.addEventListener("click", function () {
    var cur = root.dataset.theme || "light";
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

  // likes: shared counter per story (no login), one like per browser
  var likeBtns = document.querySelectorAll("[data-like-key]");
  if (likeBtns.length) {
    var key = likeBtns[0].dataset.likeKey, api = "https://abacus.jasoncameron.dev/", ns = "totalmarket";
    var liked = false;
    try { liked = localStorage.getItem("tm-like-" + key) === "1"; } catch (e) {}
    function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + "k" : String(n); }
    function paint(n) {
      likeBtns.forEach(function (b) {
        b.classList.toggle("liked", liked);
        b.setAttribute("aria-pressed", liked ? "true" : "false");
        var lc = b.querySelector(".lc");
        if (lc) lc.textContent = (typeof n === "number" && n > 0) ? fmt(n) + (liked ? " liked" : " likes") : (liked ? "Liked" : "Like");
      });
    }
    var count = null;
    paint(count);
    fetch(api + "get/" + ns + "/" + key).then(function (r) { return r.ok ? r.json() : { value: 0 }; })
      .then(function (d) { count = d.value || 0; paint(count); }).catch(function () {});
    likeBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        if (liked) { b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop"); return; }
        liked = true;
        try { localStorage.setItem("tm-like-" + key, "1"); } catch (e) {}
        if (window.gtag) gtag("event", "like_story", { story: key });
        if (typeof count === "number") count += 1;
        paint(count);
        likeBtns.forEach(function (o) { o.classList.add("pop"); });
        fetch(api + "hit/" + ns + "/" + key).then(function (r) { return r.json(); })
          .then(function (d) { if (d && typeof d.value === "number") { count = d.value; paint(count); } }).catch(function () {});
      });
    });
  }

  // comments: load giscus when the section is close to view, matching the site theme
  var gc = document.querySelector(".giscus[data-repo]");
  if (gc) {
    var loaded = false;
    function loadGiscus() {
      if (loaded) return; loaded = true;
      var s = document.createElement("script");
      s.src = "https://giscus.app/client.js"; s.async = true; s.crossOrigin = "anonymous";
      var a = { repo: gc.dataset.repo, "repo-id": gc.dataset.repoId, category: gc.dataset.category, "category-id": gc.dataset.categoryId,
        mapping: "pathname", strict: "1", "reactions-enabled": "1", "emit-metadata": "0", "input-position": "top",
        theme: (root.dataset.theme === "dark") ? "transparent_dark" : "light", lang: "en", loading: "lazy" };
      Object.keys(a).forEach(function (k) { s.setAttribute("data-" + k, a[k]); });
      gc.appendChild(s);
    }
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (en) { if (en.some(function (x) { return x.isIntersecting; })) { loadGiscus(); io.disconnect(); } }, { rootMargin: "600px" });
      io.observe(gc);
    } else loadGiscus();
    document.querySelectorAll('a[href="#comments"]').forEach(function (l) { l.addEventListener("click", loadGiscus); });
  }

  // floating like/comment bar: show after scrolling past the headline, hide at the comments
  var fab = document.querySelector(".fab"), cms = document.getElementById("comments");
  if (fab) {
    function fabCheck() {
      var y = window.scrollY, nearEnd = cms && cms.getBoundingClientRect().top < window.innerHeight * 0.8;
      fab.classList.toggle("show", y > 500 && !nearEnd);
    }
    window.addEventListener("scroll", fabCheck, { passive: true }); fabCheck();
  }

  // analytics events: share clicks and comment opens
  if (window.gtag) {
    document.querySelectorAll(".share a, .share .copy").forEach(function (a) {
      a.addEventListener("click", function () { gtag("event", "share", { method: a.textContent.replace("Share on ", "").trim() }); });
    });
    document.querySelectorAll('a[href="#comments"]').forEach(function (a) {
      a.addEventListener("click", function () { gtag("event", "open_comments"); });
    });
  }

  // search
  var q = document.getElementById("q"), box = document.getElementById("qres"), idx = null, base = ((document.querySelector(".brand") || {}).getAttribute ? document.querySelector(".brand").getAttribute("href") : "/").replace(/hi\/$/, "");
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

// ---- market session status (from NSE trading hours + holiday list; schedule-based, not live data)
(function () {
  var els = document.querySelectorAll("[data-mstatus]"), nh = document.querySelectorAll("[data-nextholiday]");
  if (!els.length && !nh.length) return;
  var base = ((document.querySelector(".brand") || {getAttribute: function () { return "/"; }}).getAttribute("href") || "/").replace(/hi\/$/, "");
  fetch(base + "market-calendar.json").then(function (r) { return r.json(); }).then(function (c) {
    function ist() { var d = new Date(); return new Date(d.getTime() + (d.getTimezoneOffset() + 330) * 60000); }
    function iso(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
    function mins(t) { var p = t.split(":"); return +p[0] * 60 + +p[1]; }
    function isTrading(d) { var w = d.getDay(); return w !== 0 && w !== 6 && c.holidays.indexOf(iso(d)) < 0; }
    var now = ist(), m = now.getHours() * 60 + now.getMinutes(), h = c.hours, label, cls;
    function nextSession() { var d = new Date(now); do { d.setDate(d.getDate() + 1); } while (!isTrading(d)); return d.toLocaleDateString("en-IN", {weekday: "short", day: "numeric", month: "short"}); }
    if (!isTrading(now)) {
      var hol = c.names[iso(now)];
      label = "Market closed" + (hol ? " · " + hol : " · weekend") + " · next " + nextSession() + " 9:15";
      cls = "closed";
    } else if (m < mins(h.preOpen[0])) { label = "Pre-market · opens 9:15 am IST"; cls = "pre"; }
    else if (m < mins(h.normal[0])) { label = "Pre-open session"; cls = "pre"; }
    else if (m < mins(h.normal[1])) { label = "Market open · closes 3:30 pm IST"; cls = "open"; }
    else if (m < mins(h.closing[1])) { label = "Closing session"; cls = "pre"; }
    else { label = "Market closed · next " + nextSession() + " 9:15"; cls = "closed"; }
    els.forEach(function (el) { el.textContent = label; el.classList.add("ms-" + cls); });
    var t = iso(now), nxt = c.holidays.filter(function (x) { return x >= t; })[0];
    nh.forEach(function (el) {
      if (!nxt) { el.textContent = "—"; return; }
      var d = new Date(nxt + "T00:00:00");
      el.innerHTML = d.toLocaleDateString("en-IN", {weekday: "short", day: "numeric", month: "short"}) + "<small>" + (c.names[nxt] || "") + "</small>";
    });
  }).catch(function () { els.forEach(function (el) { el.style.display = "none"; }); });
})();

// ---- corporate events type filter
(function () {
  var chips = document.getElementById("evchips"), list = document.getElementById("evlist");
  if (!chips || !list) return;
  chips.addEventListener("click", function (ev) {
    var b = ev.target.closest(".chipf"); if (!b) return;
    chips.querySelectorAll(".chipf").forEach(function (o) { o.classList.toggle("on", o === b); });
    var c = b.dataset.cat;
    list.querySelectorAll("tr[data-type]").forEach(function (tr) { tr.hidden = c !== "all" && tr.dataset.type !== c; });
  });
})();

// ---- report archive: find by date
(function () {
  var inp = document.getElementById("archdate"), clr = document.getElementById("archclear"), msg = document.getElementById("archmsg"), arch = document.getElementById("archive");
  if (!inp || !arch) return;
  function show(d) {
    var hits = 0;
    arch.querySelectorAll("li[data-date]").forEach(function (li) { var ok = !d || li.dataset.date === d; li.hidden = !ok; if (ok) hits++; });
    arch.querySelectorAll("section.arch").forEach(function (s) { s.hidden = !s.querySelector("li:not([hidden])"); });
    msg.textContent = d ? (hits ? hits + " report found" : "No report for that date (weekend, holiday or before our archive began).") : "";
  }
  inp.addEventListener("change", function () { show(inp.value); });
  clr.addEventListener("click", function () { inp.value = ""; show(""); });
})();

// ---- v2: segmented tabs (dashboard, earnings) + close open menus on outside click / Escape
(function () {
  document.querySelectorAll(".segs").forEach(function (group) {
    var btns = group.querySelectorAll(".seg[data-panel]");
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        btns.forEach(function (o) {
          var on = o === b; o.classList.toggle("on", on); o.setAttribute("aria-pressed", on ? "true" : "false");
          var p = document.getElementById(o.dataset.panel); if (p) p.hidden = !on;
        });
      });
    });
  });
  function closeAll(except) { document.querySelectorAll("details.more[open],details.mnav[open]").forEach(function (d) { if (d !== except) d.open = false; }); }
  document.addEventListener("click", function (ev) { closeAll(ev.target.closest("details.more,details.mnav")); });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") closeAll(null); });
})();

// ---- v2: interactive index charts with TradingView Lightweight Charts (our own EOD data).
// The server-rendered SVG chart stays in place if the library cannot load.
(function () {
  var boxes = document.querySelectorAll(".lwc[data-series]");
  if (!boxes.length) return;
  var SRC = "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js";
  var started = false;
  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function draw(box) {
    if (box.dataset.done || !window.LightweightCharts || box.offsetWidth < 50) return;
    var pts; try { pts = JSON.parse(box.dataset.series); } catch (e) { return; }
    if (!pts || pts.length < 2) return;
    var up = pts[pts.length - 1][1] >= pts[0][1], col = up ? css("--up") || "#16A34A" : css("--down") || "#DC2626";
    var holder = document.createElement("div"); holder.className = "lwc-chart";
    var svg = box.querySelector("svg");
    try {
      var chart = LightweightCharts.createChart(holder, {
        height: 260, autoSize: true,
        layout: { background: { type: "solid", color: "transparent" }, textColor: css("--muted") || "#5B6B82", fontFamily: "Inter, system-ui, sans-serif" },
        grid: { vertLines: { visible: false }, horzLines: { color: css("--line") || "#E2E8F0" } },
        rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
        crosshair: { mode: 1 }, handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
        handleScale: { mouseWheel: false, pinch: true, axisPressedMouseMove: true }
      });
      var s = chart.addAreaSeries({ lineColor: col, topColor: col + "40", bottomColor: col + "05", lineWidth: 2, priceLineVisible: false });
      s.setData(pts.map(function (p) { return { time: p[0], value: p[1] }; }));
      chart.timeScale().fitContent();
      if (svg) svg.style.display = "none";
      box.appendChild(holder);
      var a = document.createElement("p"); a.className = "lwc-attr";
      a.innerHTML = 'Chart: <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">TradingView Lightweight Charts™</a> · data: TotalMarket daily closes';
      box.appendChild(a);
      box.dataset.done = "1";
    } catch (e) { if (svg) svg.style.display = ""; holder.remove(); }
  }
  function drawVisible() { boxes.forEach(function (b) { if (!b.closest("[hidden]")) draw(b); }); }
  function start() {
    if (started) return; started = true;
    if (window.LightweightCharts) return drawVisible();
    var sc = document.createElement("script"); sc.src = SRC; sc.async = true; sc.crossOrigin = "anonymous";
    sc.onload = drawVisible; document.head.appendChild(sc);
  }
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (en) { if (en.some(function (x) { return x.isIntersecting; })) { start(); io.disconnect(); } }, { rootMargin: "300px" });
    boxes.forEach(function (b) { io.observe(b); });
  } else start();
  document.addEventListener("click", function (ev) { if (ev.target.closest(".seg")) setTimeout(drawVisible, 30); });
})();
