/* TotalMarket calculators: gold value, SIP, EMI. Plain JS, no libraries. */
(function () {
  var inr = function (n, d) {
    return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: d || 0, minimumFractionDigits: d || 0 });
  };
  var words = function (n) {
    if (n >= 1e7) return "₹" + (n / 1e7).toFixed(2) + " crore";
    if (n >= 1e5) return "₹" + (n / 1e5).toFixed(2) + " lakh";
    return inr(n);
  };
  var num = function (f, k) { var v = parseFloat(f.querySelector('[name="' + k + '"]').value); return isFinite(v) ? v : 0; };
  var out = function (box, k) { return box.querySelector('[data-out="' + k + '"]'); };

  function gold(box) {
    var grams = num(box, "grams");
    var pur = box.querySelector('[name="purity"]').value;
    var gst = box.querySelector('[name="gst"]').checked;
    var rate = parseFloat(box.dataset[pur]);
    var perUnit = pur === "silver" ? rate / 1000 : rate / 10;
    var v = grams * perUnit;
    var total = gst ? v * 1.03 : v;
    out(box, "value").textContent = inr(total);
    out(box, "explain").textContent = grams + " g × " + inr(perUnit, 2) + " per gram = " + inr(v) +
      (gst ? " + 3% GST " + inr(v * 0.03) : " (before GST and making charges)");
  }

  function sip(box) {
    var amt = num(box, "amt"), rate = num(box, "rate"), yrs = Math.round(num(box, "yrs")), step = num(box, "step");
    var i = rate / 100 / 12, value = 0, invested = 0, m = amt;
    for (var y = 0; y < yrs; y++) {
      for (var k = 0; k < 12; k++) { value = (value + m) * (1 + i); invested += m; }
      m = m * (1 + step / 100);
    }
    var gain = value - invested;
    out(box, "invested").textContent = words(invested);
    out(box, "gain").textContent = words(gain);
    out(box, "value").textContent = words(value);
    out(box, "bar").style.width = (value > 0 ? (invested / value) * 100 : 0) + "%";
    out(box, "explain").textContent = value > 0
      ? "The blue part of the bar is your own money (" + Math.round(invested / value * 100) + "%); the rest is growth from compounding. Try adding 5 years to see how fast the growth part takes over."
      : "";
  }

  function emi(box) {
    var P = num(box, "amt"), rate = num(box, "rate"), yrs = Math.round(num(box, "yrs"));
    var r = rate / 100 / 12, n = yrs * 12;
    if (!P || !r || !n) return;
    var e = P * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
    var total = e * n, interest = total - P;
    out(box, "emi").textContent = inr(e);
    out(box, "interest").textContent = words(interest);
    out(box, "total").textContent = words(total);
    out(box, "bar").style.width = (P / total * 100) + "%";
    out(box, "explain").textContent = "The blue part of the bar is the loan itself; the rest is interest. In month one, " +
      inr(P * r) + " of your " + inr(e) + " EMI is interest.";
    var bal = P, rows = "";
    for (var y = 1; y <= yrs; y++) {
      var pp = 0, ip = 0;
      for (var k = 0; k < 12; k++) { var it = bal * r; ip += it; pp += e - it; bal -= e - it; }
      rows += "<tr><th scope=\"row\">Year " + y + "</th><td class=\"num\">" + inr(pp) + "</td><td class=\"num\">" + inr(ip) + "</td><td class=\"num\">" + inr(Math.max(bal, 0)) + "</td></tr>";
    }
    out(box, "sched").innerHTML = rows;
  }

  var fns = { gold: gold, sip: sip, emi: emi };
  document.querySelectorAll("[data-calc]").forEach(function (box) {
    var fn = fns[box.dataset.calc];
    if (!fn) return;
    box.addEventListener("input", function () { fn(box); });
    box.addEventListener("change", function () { fn(box); });
    fn(box);
  });
})();
