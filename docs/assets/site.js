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
        theme: (root.dataset.theme === "light") ? "light" : "transparent_dark", lang: "en", loading: "lazy" };
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
