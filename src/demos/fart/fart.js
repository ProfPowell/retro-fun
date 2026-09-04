/*!
 * <fart> v2.0.0 "Dutch Oven" — the lowest of the low-class web components.
 *
 * A rebirth of fart.js (https://github.com/74656c/fart.js) for the modern
 * web: zero dependencies, zero audio files, zero dignity. Every fart is
 * synthesized live with the Web Audio API, so no two rips are alike.
 *
 * Usage:
 *   <script src="fart.js"></script>
 *   <fart>click me</fart>
 *   <fart on="hover">hover me</fart>
 *   <fart on="ambush" lurk="15-60"></fart>   <!-- it waits. it watches. -->
 *
 * Attributes:
 *   on="click|hover|ambush|load"   default: click
 *   type="classic|squeak|bomber|machinegun|question|random"  default: random
 *   volume="0..1"                  default: 0.8
 *   lurk="MIN-MAX"                 ambush delay range in seconds, default 15-75
 *   no-cloud                       silent but deadly (sound only, no visual)
 *
 * JS API: FART.rip(type, x, y, volume)
 *
 * Yes, custom elements are supposed to have a hyphen. This one doesn't.
 * It knows what it is. The W3C cannot hurt it.
 */
(function () {
  "use strict";

  var ctx = null;
  var noiseBuf = null;
  var ready = false;
  var pendingArms = [];

  // ------------------------------------------------------------ audio core
  function ensureCtx() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function getNoise() {
    if (!noiseBuf) {
      noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      var d = noiseBuf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    return noiseBuf;
  }

  function rnd(a, b) { return a + Math.random() * (b - a); }

  // Random-walk gate: the sputter is the soul of the fart.
  function sputterCurve(n, openness, wildness) {
    var c = new Float32Array(n);
    var g = 0.7;
    for (var i = 0; i < n; i++) {
      g += (Math.random() - 0.5) * wildness;
      g = Math.max(0.05, Math.min(1, g));
      var p = i / (n - 1);
      var env = Math.min(1, p * 18) * Math.pow(1 - p, 0.6);
      c[i] = g * env * openness;
    }
    return c;
  }

  function freqCurve(n, f0, drop, flutter, dur, riseTail) {
    var c = new Float32Array(n);
    var wob = 0;
    for (var i = 0; i < n; i++) {
      var p = i / (n - 1);
      wob += (Math.random() - 0.5) * 0.12;
      wob *= 0.85;
      var f = f0 * (1 - drop * p) * (1 + 0.16 * Math.sin(2 * Math.PI * flutter * p * dur) + wob);
      if (riseTail && p > 0.72) f *= 1 + (p - 0.72) * 1.6; // the interrogative lift
      c[i] = Math.max(25, f);
    }
    return c;
  }

  function body(t0, dur, f0, drop, flutter, filterHz, vol, riseTail) {
    var n = Math.max(24, Math.floor(dur * 220));
    var osc = ctx.createOscillator();
    osc.type = "sawtooth";
    osc.frequency.setValueCurveAtTime(freqCurve(n, f0, drop, flutter, dur, riseTail), t0, dur);

    var gain = ctx.createGain();
    gain.gain.setValueCurveAtTime(sputterCurve(n, vol, 0.55), t0, dur);

    var filt = ctx.createBiquadFilter();
    filt.type = "lowpass";
    filt.Q.value = 7;
    filt.frequency.setValueAtTime(filterHz, t0);
    filt.frequency.exponentialRampToValueAtTime(filterHz * 0.55, t0 + dur);

    // raspy air layer
    var nz = ctx.createBufferSource();
    nz.buffer = getNoise();
    nz.loop = true;
    var nzf = ctx.createBiquadFilter();
    nzf.type = "bandpass";
    nzf.frequency.value = 190;
    nzf.Q.value = 1.6;
    var nzg = ctx.createGain();
    nzg.gain.setValueCurveAtTime(sputterCurve(n, vol * 0.4, 0.7), t0, dur);

    osc.connect(gain).connect(filt).connect(ctx.destination);
    nz.connect(nzf).connect(nzg).connect(filt);
    osc.start(t0); osc.stop(t0 + dur + 0.05);
    nz.start(t0); nz.stop(t0 + dur + 0.05);
    osc.onended = function () { gain.disconnect(); nzg.disconnect(); filt.disconnect(); };
  }

  var TYPES = {
    classic: function (t0, vol) {
      body(t0, rnd(0.55, 1.1), rnd(72, 105), rnd(0.25, 0.4), rnd(20, 34), rnd(360, 520), vol, false);
    },
    squeak: function (t0, vol) {
      var dur = rnd(0.28, 0.45);
      var osc = ctx.createOscillator();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(rnd(480, 720), t0);
      osc.frequency.exponentialRampToValueAtTime(rnd(140, 220), t0 + dur);
      var vib = ctx.createOscillator();
      vib.frequency.value = 9;
      var vibG = ctx.createGain();
      vibG.gain.value = 28;
      vib.connect(vibG).connect(osc.frequency);
      var g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(vol * 0.7, t0 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(g).connect(ctx.destination);
      osc.start(t0); osc.stop(t0 + dur);
      vib.start(t0); vib.stop(t0 + dur);
      osc.onended = function () { g.disconnect(); };
    },
    bomber: function (t0, vol) {
      var dur = rnd(1.7, 2.5);
      body(t0, dur, rnd(48, 60), 0.15, rnd(14, 19), 240, vol, false);
      var sub = ctx.createOscillator();
      sub.type = "sine";
      sub.frequency.setValueAtTime(38, t0);
      var g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(vol * 0.5, t0 + 0.08);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      sub.connect(g).connect(ctx.destination);
      sub.start(t0); sub.stop(t0 + dur);
      sub.onended = function () { g.disconnect(); };
    },
    machinegun: function (t0, vol) {
      var shots = 5 + Math.floor(Math.random() * 5);
      var t = t0;
      for (var i = 0; i < shots; i++) {
        body(t, rnd(0.07, 0.13), rnd(90, 130), 0.3, 40, 500, vol * rnd(0.7, 1), false);
        t += rnd(0.1, 0.16);
      }
    },
    question: function (t0, vol) {
      body(t0, rnd(0.6, 0.95), rnd(70, 95), 0.3, rnd(20, 30), 430, vol, true);
    }
  };
  var TYPE_NAMES = Object.keys(TYPES);

  function rip(type, x, y, volume, noCloud) {
    var c = ensureCtx();
    if (!c) return;
    ready = true;
    if (!type || type === "random" || !TYPES[type]) {
      type = TYPE_NAMES[Math.floor(Math.random() * TYPE_NAMES.length)];
    }
    TYPES[type](c.currentTime + 0.02, Math.max(0, Math.min(1, volume == null ? 0.8 : volume)));
    if (!noCloud) cloud(x == null ? rnd(0.2, 0.8) * innerWidth : x,
                        y == null ? rnd(0.2, 0.8) * innerHeight : y,
                        type === "bomber" ? 1.6 : type === "squeak" ? 0.6 : 1);
  }

  // ------------------------------------------------------------ the cloud
  function cloud(x, y, scale) {
    var wrap = document.createElement("div");
    wrap.style.cssText = "position:fixed;left:" + x + "px;top:" + y +
      "px;pointer-events:none;z-index:2147483647;";
    var blobs = 6 + Math.floor(Math.random() * 4);
    var maxDur = 0;
    for (var i = 0; i < blobs; i++) {
      var b = document.createElement("div");
      var s = rnd(28, 85) * scale;
      var hue = rnd(70, 95);
      b.style.cssText = "position:absolute;width:" + s + "px;height:" + s +
        "px;left:" + (-s / 2) + "px;top:" + (-s / 2) +
        "px;border-radius:50%;filter:blur(" + rnd(4, 9) +
        "px);background:radial-gradient(circle,hsla(" + hue + ",65%,55%,.85),hsla(" +
        hue + ",60%,35%,0));";
      wrap.appendChild(b);
      var dur = rnd(900, 1700);
      maxDur = Math.max(maxDur, dur);
      b.animate([
        { transform: "translate(0,0) scale(.25)", opacity: 0.9 },
        { transform: "translate(" + rnd(-70, 70) * scale + "px," +
          (rnd(-110, -30) * scale) + "px) scale(" + rnd(1.2, 2) + ")", opacity: 0 }
      ], { duration: dur, easing: "cubic-bezier(.2,.6,.4,1)" });
    }
    document.body.appendChild(wrap);
    setTimeout(function () { wrap.remove(); }, maxDur + 100);
  }

  // ------------------------------------------------------------ the tag
  function center(el) {
    var r = el.getBoundingClientRect();
    return r.width || r.height
      ? { x: r.left + r.width / 2, y: r.top + r.height / 2 }
      : { x: null, y: null };
  }

  function arm(el) {
    if (el.__farted) return;
    el.__farted = true;
    var on = (el.getAttribute("on") || "click").toLowerCase();
    var type = el.getAttribute("type") || "random";
    var vol = parseFloat(el.getAttribute("volume"));
    if (isNaN(vol)) vol = 0.8;
    var noCloud = el.hasAttribute("no-cloud");
    var fire = function (x, y) { rip(type, x, y, vol, noCloud); };

    if (on === "click") {
      el.addEventListener("click", function (e) { fire(e.clientX, e.clientY); });
    } else if (on === "hover") {
      var last = 0;
      el.addEventListener("mouseenter", function () {
        var now = Date.now();
        if (now - last < 700) return;
        last = now;
        var c = center(el);
        fire(c.x, c.y);
      });
    } else if (on === "ambush" || on === "load") {
      // Browsers require a user gesture before flatulence. Them's the rules.
      var go = function () {
        if (on === "load") {
          var c = center(el);
          fire(c.x, c.y);
          return;
        }
        var range = (el.getAttribute("lurk") || "15-75").split("-");
        var lo = parseFloat(range[0]) || 15;
        var hi = parseFloat(range[1]) || lo + 60;
        (function schedule() {
          if (!el.isConnected) return;   // the fart has been unplugged
          setTimeout(function () {
            if (!el.isConnected) return;
            if (!document.hidden) fire(null, null);
            schedule();
          }, rnd(lo, hi) * 1000);
        })();
      };
      if (ready) go(); else pendingArms.push(go);
    }
  }

  function sweep(root) {
    var list = (root.querySelectorAll ? root.querySelectorAll("fart") : []);
    for (var i = 0; i < list.length; i++) arm(list[i]);
    if (root.tagName === "FART") arm(root);
  }

  function unlock() {
    ensureCtx();
    ready = true;
    while (pendingArms.length) pendingArms.shift()();
    removeEventListener("pointerdown", unlock, true);
    removeEventListener("keydown", unlock, true);
  }

  function init() {
    var st = document.createElement("style");
    st.textContent = "fart{display:inline-block;cursor:pointer;-webkit-user-select:none;user-select:none;}";
    document.head.appendChild(st);
    sweep(document);
    new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        for (var i = 0; i < m.addedNodes.length; i++) {
          if (m.addedNodes[i].nodeType === 1) sweep(m.addedNodes[i]);
        }
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
    addEventListener("pointerdown", unlock, true);
    addEventListener("keydown", unlock, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.FART = {
    rip: rip,
    types: TYPE_NAMES.concat("random"),
    version: "2.0.0-dutch-oven"
  };
})();
