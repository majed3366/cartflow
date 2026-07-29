/**
 * CartFlow Landing Page Reality Validation V1 — anonymous behavioural beacons.
 * No PII. Allowed events only. Does not alter layout or copy.
 */
(function () {
  "use strict";

  var ENDPOINT = "/api/landing/event";
  var SESSION_KEY = "cf_lp_sid_v1";
  var fired = Object.create(null);

  function sessionId() {
    try {
      var s = sessionStorage.getItem(SESSION_KEY);
      if (s && /^[A-Za-z0-9_-]{8,64}$/.test(s)) return s;
      s =
        "s_" +
        Math.random().toString(36).slice(2) +
        Date.now().toString(36);
      sessionStorage.setItem(SESSION_KEY, s);
      return s;
    } catch (e) {
      return "";
    }
  }

  function deviceClass() {
    var w = window.innerWidth || 0;
    if (w < 768) return "mobile";
    if (w < 1100) return "tablet";
    return "desktop";
  }

  function send(eventName, section) {
    if (!eventName) return;
    var body = {
      event: eventName,
      section: section || null,
      device: deviceClass(),
      session_key: sessionId(),
    };
    try {
      if (navigator.sendBeacon) {
        var blob = new Blob([JSON.stringify(body)], {
          type: "application/json",
        });
        navigator.sendBeacon(ENDPOINT, blob);
        return;
      }
    } catch (e) {}
    try {
      fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        keepalive: true,
        credentials: "same-origin",
      }).catch(function () {});
    } catch (e2) {}
  }

  function once(eventName, section) {
    var k = eventName + "|" + (section || "");
    if (fired[k]) return;
    fired[k] = true;
    send(eventName, section);
  }

  send("landing_opened", "page");

  function observeViews() {
    if (!("IntersectionObserver" in window)) return;
    var nodes = document.querySelectorAll("[data-lp-view]");
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting || entry.intersectionRatio < 0.35) return;
          var ev = entry.target.getAttribute("data-lp-view");
          var sec = entry.target.getAttribute("data-lp-section") || ev;
          if (ev) once(ev, sec);
        });
      },
      { threshold: [0.35] }
    );
    nodes.forEach(function (n) {
      io.observe(n);
    });
  }

  function bindCtas() {
    document.addEventListener(
      "click",
      function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest("a[data-lp-cta]") : null;
        if (!a) return;
        var kind = a.getAttribute("data-lp-cta");
        if (kind === "hero_signup") {
          send("hero_cta_clicked", "hero");
          send("signup_clicked", "hero");
        } else if (kind === "final_signup") {
          send("signup_clicked", "final_cta");
        } else if (kind === "signup") {
          send("signup_clicked", "nav_or_other");
        } else if (kind === "login") {
          send("login_clicked", a.closest("header") ? "nav" : "other");
        }
      },
      true
    );
  }

  function bindScroll() {
    var marks = [
      [0.25, "scroll_25"],
      [0.5, "scroll_50"],
      [0.75, "scroll_75"],
      [0.98, "scroll_100"],
    ];
    function onScroll() {
      var doc = document.documentElement;
      var max = Math.max(1, (doc.scrollHeight || 1) - (window.innerHeight || 0));
      var ratio = (window.scrollY || doc.scrollTop || 0) / max;
      marks.forEach(function (m) {
        if (ratio >= m[0]) once(m[1], "page");
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  function bindExit() {
    function exit() {
      once("page_exit", "page");
    }
    window.addEventListener("pagehide", exit);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") exit();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      observeViews();
      bindCtas();
      bindScroll();
      bindExit();
    });
  } else {
    observeViews();
    bindCtas();
    bindScroll();
    bindExit();
  }
})();
