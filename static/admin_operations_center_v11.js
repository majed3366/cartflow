/* Local filter / mobile segments for /admin/operations V1.1. No network. */
(function () {
  var root = document.getElementById("ops-v11");
  if (!root) return;

  var filterBtns = root.querySelectorAll(".filters [data-filter]");
  var emptyPlatform = root.querySelector("#empty-platform");

  function applyFilter(kind) {
    filterBtns.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-filter") === kind ? "true" : "false");
    });
    root.querySelectorAll("#needs .case").forEach(function (c) {
      var scope = c.getAttribute("data-scope") || "";
      c.hidden = kind !== "all" && scope.indexOf(kind) === -1;
    });
    var hasPlatform = root.querySelectorAll('#needs .case[data-scope="platform"]').length > 0;
    if (emptyPlatform) emptyPlatform.hidden = !(kind === "platform" && !hasPlatform);
  }
  filterBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      applyFilter(b.getAttribute("data-filter"));
    });
  });

  var segBtns = root.querySelectorAll(".segs [data-pane]");
  var panes = root.querySelectorAll(".m-pane");
  function applyPane(pane) {
    segBtns.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-pane") === pane ? "true" : "false");
    });
    if (window.matchMedia("(max-width: 900px)").matches) {
      panes.forEach(function (p) {
        p.hidden = p.getAttribute("data-pane") !== pane;
      });
    } else {
      panes.forEach(function (p) {
        p.hidden = false;
      });
    }
  }
  segBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      applyPane(b.getAttribute("data-pane"));
    });
  });
  window.addEventListener("resize", function () {
    var active = root.querySelector(".segs [aria-pressed='true']");
    applyPane(active ? active.getAttribute("data-pane") : "needs");
  });
  applyPane("needs");

  root.querySelectorAll("a[href^='#case-']").forEach(function (a) {
    a.addEventListener("click", function (e) {
      var id = a.getAttribute("href").slice(1);
      var el = document.getElementById(id);
      if (!el) return;
      e.preventDefault();
      if (el.tagName === "DETAILS") el.open = true;
      applyFilter("all");
      applyPane(id.indexOf("case-wa-") === 0 || id.indexOf("monitor-") === 0 ? "merchants" : "needs");
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
})();
