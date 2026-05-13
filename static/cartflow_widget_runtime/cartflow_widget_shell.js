/**
 * Single storefront widget shell — one bubble, stable chrome, content mount only.
 * Flows render inside the shell via Ui; flows do not own outer widget structure.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var WIDGET_BODY_SELECTOR = ".cartflow-widget-body";
  var HEADER_DEFAULT = "مساعدة";

  function shellLog(tag, meta) {
    try {
      if (meta !== undefined && meta !== null) {
        console.log(tag, meta);
      } else {
        console.log(tag);
      }
    } catch (eL) {}
  }

  function stShell() {
    try {
      return Cf.State.internals.shell;
    } catch (eS) {
      return null;
    }
  }

  function patchShell(patch) {
    var sh = stShell();
    if (!sh || !patch) {
      return;
    }
    var k;
    for (k in patch) {
      if (Object.prototype.hasOwnProperty.call(patch, k)) {
        sh[k] = patch[k];
      }
    }
  }

  /** Canonical singleton: [data-cartflow-bubble][data-cf-shell="1"] */
  function rootFromDom() {
    var el = document.querySelector('[data-cartflow-bubble][data-cf-shell="1"]');
    if (el) {
      return el;
    }
    el = document.querySelector("[data-cartflow-bubble]");
    return el;
  }

  /**
   * Remove duplicate bubbles; prefer the marked shell instance.
   */
  function dedupeShellRoots() {
    var all = document.querySelectorAll("[data-cartflow-bubble]");
    if (all.length <= 1) {
      return rootFromDom();
    }
    var keeper =
      document.querySelector('[data-cartflow-bubble][data-cf-shell="1"]') || all[0];
    var i;
    for (i = 0; i < all.length; i++) {
      if (all[i] !== keeper) {
        try {
          all[i].parentNode.removeChild(all[i]);
        } catch (eR) {}
      }
    }
    return keeper;
  }

  function getRoot() {
    return rootFromDom();
  }

  function getContentMount() {
    var w = rootFromDom();
    if (!w) {
      return null;
    }
    return w.querySelector(WIDGET_BODY_SELECTOR);
  }

  function getFooter() {
    var w = rootFromDom();
    if (!w) {
      return null;
    }
    return w.querySelector("[data-cf-shell-footer]");
  }

  function getLoadingEl() {
    var w = rootFromDom();
    if (!w) {
      return null;
    }
    return w.querySelector("[data-cf-shell-loading]");
  }

  function clearContentMount() {
    var mount = getContentMount();
    if (!mount) {
      return;
    }
    while (mount.firstChild) {
      mount.removeChild(mount.firstChild);
    }
  }

  function ensureLauncherChip(w) {
    var chip = w.querySelector("[data-cf-shell-launcher-chip]");
    if (chip) {
      return chip;
    }
    chip = document.createElement("button");
    chip.type = "button";
    chip.setAttribute("data-cf-shell-launcher-chip", "1");
    chip.setAttribute("aria-label", "فتح المساعدة");
    chip.textContent = "?";
    chip.style.cssText =
      "display:none;box-sizing:border-box;position:absolute;left:0;top:0;width:100%;height:100%;" +
      "align-items:center;justify-content:center;margin:0;border:0;background:transparent;" +
      "cursor:pointer;color:#f8fafc;font-size:22px;font-weight:700;line-height:1;padding:0;";
    w.appendChild(chip);
    chip.addEventListener(
      "click",
      function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        shellLog("[CF SHELL LAUNCHER OPEN]", {});
        expandShell();
      },
      false
    );
    return chip;
  }

  function expandShell() {
    var w = rootFromDom();
    if (!w || w.getAttribute("data-cf-shell-minimized") !== "1") {
      return;
    }
    try {
      var ph =
        Cf.Config && Cf.Config.merchant && Cf.Config.merchant().widget_primary_color;
      ensureShell(ph);
    } catch (ePh) {
      ensureShell();
    }
    w = rootFromDom();
    if (!w) {
      return;
    }
    var inner = w.querySelector("[data-cf-shell-inner]");
    var chip = w.querySelector("[data-cf-shell-launcher-chip]");
    if (inner) {
      inner.style.display = "";
    }
    if (chip) {
      chip.style.display = "none";
    }
    try {
      w.style.visibility = "visible";
      w.style.overflow = "";
      w.style.display = "block";
    } catch (eVi) {}
    w.removeAttribute("data-cf-shell-minimized");
    patchShell({ isMinimized: false, isOpen: true });
    shellLog("[CF SHELL EXPAND]", {});
  }

  /** Cart recovery „لا”: keep content; shrink to launcher chip only. */
  function minimizeLauncher() {
    var w = rootFromDom();
    if (!w) {
      return;
    }
    dedupeShellRoots();
    w = rootFromDom();
    if (!w) {
      return;
    }
    try {
      window.clearTimeout(showSuccess._t);
    } catch (eCt) {}
    showSuccess._t = null;
    try {
      hideFooterMessage();
    } catch (eFm) {}

    ensureLauncherChip(w);
    var inner = w.querySelector("[data-cf-shell-inner]");
    var chip = w.querySelector("[data-cf-shell-launcher-chip]");
    if (inner) {
      inner.style.display = "none";
    }
    if (chip) {
      chip.style.display = "flex";
    }

    w.setAttribute("data-cf-shell-minimized", "1");
    try {
      w.style.boxSizing = "border-box";
      w.style.display = "block";
      w.style.visibility = "visible";
      w.style.position = "fixed";
      w.style.zIndex = "2147483640";
      w.style.right = "max(12px,env(safe-area-inset-right))";
      w.style.bottom = "max(12px,env(safe-area-inset-bottom))";
      w.style.left = "";
      w.style.top = "";
      w.style.width = "52px";
      w.style.height = "52px";
      w.style.maxWidth = "52px";
      w.style.padding = "0";
      w.style.margin = "0";
      w.style.borderRadius = "999px";
      w.style.overflow = "hidden";
      w.style.cursor = "default";
      w.style.background =
        "linear-gradient(165deg,#1e1b4b 0%,#312e81 52%,#1e3a5f 100%)";
      w.style.border = "1px solid rgba(99,102,241,.5)";
      w.style.boxShadow = "0 10px 28px rgba(2,6,23,.52)";
      w.style.fontSize = "0";
      w.style.lineHeight = "1";
      w.style.fontFamily =
        "system-ui,-apple-system,Segoe UI,Roboto,sans-serif";
    } catch (eStl) {}

    patchShell({ isMinimized: true, isOpen: true });
    shellLog("[CF SHELL MINIMIZE]", { mode: "launcher" });
  }

  function bindCloseButtonOnce(w) {
    var closer = w.querySelector("[data-cf-shell-close]");
    if (!closer) {
      return;
    }
    if (closer.getAttribute("data-cf-shell-bound") === "1") {
      shellLog("[CF SHELL LISTENER DUPLICATE BLOCKED]", { which: "close" });
      return;
    }
    closer.setAttribute("data-cf-shell-bound", "1");
    closer.addEventListener(
      "click",
      function (e) {
        e.preventDefault();
        e.stopPropagation();
        close({ syncDismiss: true });
      },
      false
    );
  }

  function ensureShell(primaryHex) {
    dedupeShellRoots();

    var createdNew = false;
    var w = rootFromDom();
    if (!w) {
      w = document.createElement("div");
      w.setAttribute("data-cartflow-bubble", "1");
      w.setAttribute("data-cf-reason-entry", "v2");
      w.setAttribute("data-cf-shell", "1");
      document.body.appendChild(w);
      createdNew = true;
    } else {
      if (!w.getAttribute("data-cf-shell")) {
        w.setAttribute("data-cf-shell", "1");
      }
    }

    var fill = primaryHex || "#6366F1";
    w.style.cssText =
      "position:fixed;z-index:2147483640;max-width:min(300px,calc(100vw - 20px));" +
      "right:max(12px,env(safe-area-inset-right));bottom:max(12px,env(safe-area-inset-bottom));" +
      "box-sizing:border-box;padding:11px;border-radius:14px;" +
      "background:linear-gradient(165deg,#1e1b4b 0%,#312e81 42%,#1e1b4b 100%);" +
      "color:#f1f5f9;border:1px solid rgba(99,102,241,.45);" +
      "box-shadow:0 18px 48px rgba(2,6,23,.72), inset 0 1px 0 rgba(255,255,255,.06);" +
      "font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;line-height:1.42;";

    var inner = w.querySelector("[data-cf-shell-inner]");
    if (!inner) {
      inner = document.createElement("div");
      inner.setAttribute("data-cf-shell-inner", "1");
      inner.style.cssText = "position:relative;display:block;";
      while (w.firstChild) {
        inner.appendChild(w.firstChild);
      }
      w.appendChild(inner);
    }

    if (!w.querySelector('[data-cf-chrome="1"]')) {
      var bar = document.createElement("div");
      bar.setAttribute("data-cf-chrome", "1");
      bar.style.cssText =
        "height:4px;border-radius:999px;margin:0 0 10px 0;background:" + fill + ";";
      inner.insertBefore(bar, inner.firstChild);
    } else {
      try {
        var barUp = w.querySelector('[data-cf-chrome="1"]');
        if (barUp) {
          barUp.style.background = fill;
        }
      } catch (eB) {}
    }

    if (!w.querySelector("[data-cf-shell-header]")) {
      var head = document.createElement("div");
      head.setAttribute("data-cf-shell-header", "1");
      head.style.cssText =
        "display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 6px 0;";
      var title = document.createElement("span");
      title.setAttribute("data-cf-shell-title", "1");
      title.style.cssText =
        "font-weight:700;font-size:13px;color:#eef2ff;letter-spacing:.01em;";
      title.textContent = HEADER_DEFAULT;
      var closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.setAttribute("data-cf-shell-close", "1");
      closeBtn.setAttribute("aria-label", "إغلاق");
      closeBtn.style.cssText =
        "border:0;background:transparent;color:rgba(226,232,240,.82);cursor:pointer;font-size:20px;line-height:1;padding:2px 6px;border-radius:8px;";
      closeBtn.textContent = "×";
      head.appendChild(title);
      head.appendChild(closeBtn);
      var chrome = inner.querySelector('[data-cf-chrome="1"]');
      if (chrome) {
        inner.insertBefore(head, chrome.nextSibling);
      } else {
        inner.insertBefore(head, inner.firstChild);
      }
    }

    var stage = w.querySelector("[data-cf-shell-stage]");
    if (!stage) {
      stage = document.createElement("div");
      stage.setAttribute("data-cf-shell-stage", "1");
      stage.style.cssText = "position:relative;display:block;min-height:0;";
      var legacyBody = w.querySelector(WIDGET_BODY_SELECTOR);
      if (legacyBody && legacyBody.parentNode === inner) {
        inner.insertBefore(stage, legacyBody);
        stage.appendChild(legacyBody);
      } else {
        var footRef = w.querySelector("[data-cf-shell-footer]");
        if (footRef && footRef.parentNode === inner) {
          inner.insertBefore(stage, footRef);
        } else {
          inner.appendChild(stage);
        }
      }
    }

    if (!stage.querySelector(WIDGET_BODY_SELECTOR)) {
      var mount = document.createElement("div");
      mount.className = "cartflow-widget-body";
      mount.setAttribute("data-cf-shell-content", "1");
      mount.style.cssText = "display:block;position:relative;z-index:1;min-height:0;";
      stage.appendChild(mount);
    }

    if (!stage.querySelector("[data-cf-shell-loading]")) {
      var load = document.createElement("div");
      load.setAttribute("data-cf-shell-loading", "1");
      load.style.cssText =
        "display:none;position:absolute;left:0;right:0;top:0;bottom:0;align-items:center;justify-content:center;" +
        "flex-direction:row;background:rgba(15,23,42,.45);border-radius:10px;z-index:4;font-size:12px;color:#e2e8f0;";
      load.textContent = "…";
      var mEl = stage.querySelector(WIDGET_BODY_SELECTOR);
      if (mEl) {
        stage.insertBefore(load, mEl);
      } else {
        stage.appendChild(load);
      }
    }

    if (!w.querySelector("[data-cf-shell-footer]")) {
      var foot = document.createElement("div");
      foot.setAttribute("data-cf-shell-footer", "1");
      foot.style.cssText =
        "margin-top:8px;min-height:0;font-size:12px;line-height:1.35;color:rgba(226,232,240,.92);display:none;";
      inner.appendChild(foot);
    }

    bindCloseButtonOnce(w);

    return { root: w, createdNew: createdNew };
  }

  function open(opts) {
    opts = opts || {};
    dedupeShellRoots();
    var hadRoot = !!rootFromDom();
    var r = ensureShell(opts.primaryColor);
    var w = r.root;
    try {
      if (w && w.getAttribute("data-cf-shell-minimized") === "1") {
        expandShell();
        w = rootFromDom();
      }
    } catch (eExp) {}
    if (r.createdNew) {
      shellLog("[CF SHELL OPEN]", { created: true });
    } else if (hadRoot) {
      shellLog("[CF SHELL REUSED]", { reused: true });
    } else {
      shellLog("[CF SHELL OPEN]", { created: false });
    }
    try {
      w.style.display = "block";
      w.style.visibility = "visible";
    } catch (eVis) {}
    patchShell({ isOpen: true });
    return w;
  }

  function close(opts) {
    opts = opts || {};
    try {
      window.clearTimeout(showSuccess._t);
    } catch (eCt) {}
    showSuccess._t = null;

    shellLog("[CF SHELL CLOSE]", {
      syncDismiss: !!opts.syncDismiss,
    });

    var w = rootFromDom();
    if (!w) {
      patchShell({
        isOpen: false,
        currentStep: null,
        loading: false,
        mountedView: null,
        lastTriggerSource: null,
        isMinimized: false,
      });
      return;
    }
    try {
      w.removeAttribute("data-cf-shell-minimized");
      var chin = w.querySelector("[data-cf-shell-launcher-chip]");
      var inn = w.querySelector("[data-cf-shell-inner]");
      if (chin) {
        chin.style.display = "none";
      }
      if (inn) {
        inn.style.display = "";
      }
    } catch (eMin) {}

    try {
      w.style.display = "none";
    } catch (eH) {}

    try {
      var elLoad = getLoadingEl();
      var mount = getContentMount();
      if (mount) {
        mount.style.opacity = "";
      }
      if (elLoad) {
        elLoad.style.display = "none";
      }
    } catch (eLd) {}

    clearContentMount();
    try {
      hideFooterMessage();
    } catch (eF) {}

    patchShell({
      isOpen: false,
      currentStep: null,
      loading: false,
      mountedView: null,
      lastTriggerSource: null,
      isMinimized: false,
    });

    if (opts.syncDismiss) {
      try {
        Cf.State.internals.bubbleShown = false;
      } catch (eB) {}
      try {
        if (window.CartFlowState) {
          window.CartFlowState.widgetShown = false;
        }
      } catch (eC) {}
    }
  }

  /**
   * @param {*} content HTMLElement, DocumentFragment, or string (trusted internal markup only; prefer fragment from Ui)
   * @param {string} [mountedView] optional view key for state.shell.mountedView
   */
  function setContent(content, mountedView) {
    var mount = getContentMount();
    if (!mount) {
      return;
    }
    while (mount.firstChild) {
      mount.removeChild(mount.firstChild);
    }
    try {
      hideFooterMessage();
    } catch (eF) {}
    shellLog("[CF SHELL CONTENT SET]", {
      mountedView: mountedView != null ? String(mountedView) : null,
      mode:
        content == null || content === ""
          ? "clear"
          : typeof content === "string"
          ? "html"
          : content.nodeType === 11
          ? "fragment"
          : "element",
    });
    if (content == null || content === "") {
      patchShell({ mountedView: mountedView != null ? mountedView : null });
      return;
    }
    if (typeof content === "string") {
      mount.textContent = "";
      mount.innerHTML = content;
    } else if (content.nodeType === 11) {
      mount.appendChild(content);
    } else if (content.nodeType === 1) {
      mount.appendChild(content);
    }
    patchShell({ mountedView: mountedView != null ? mountedView : null });
  }

  function setLoading(on) {
    var el = getLoadingEl();
    var mount = getContentMount();
    if (mount) {
      try {
        mount.style.opacity = on ? "0.5" : "";
      } catch (eO) {}
    }
    if (el) {
      try {
        el.style.display = on ? "flex" : "none";
      } catch (eL) {}
    }
    patchShell({ loading: !!on });
  }

  function setStep(stepName) {
    patchShell({ currentStep: stepName != null ? String(stepName) : null });
  }

  function setLastTriggerSource(tag) {
    patchShell({
      lastTriggerSource: tag != null ? String(tag) : null,
    });
  }

  function showFooterMessage(opts) {
    opts = opts || {};
    var foot = getFooter();
    if (!foot) {
      return;
    }
    var msg = opts.message != null ? String(opts.message) : "";
    if (!msg) {
      foot.style.display = "none";
      foot.textContent = "";
      return;
    }
    foot.style.display = "block";
    foot.textContent = msg;
    try {
      foot.style.color =
        opts.tone === "error"
          ? "#fecaca"
          : opts.tone === "success"
          ? "#86efac"
          : "#e2e8f0";
    } catch (eC) {}
  }

  function hideFooterMessage() {
    showFooterMessage({ message: "" });
  }

  function showError(message) {
    showFooterMessage({ message: message, tone: "error" });
  }

  function showSuccess(message) {
    showFooterMessage({ message: message, tone: "success" });
    try {
      window.clearTimeout(showSuccess._t);
    } catch (eCt) {}
    showSuccess._t = window.setTimeout(function () {
      hideFooterMessage();
    }, 3200);
  }

  var Shell = {
    open: open,
    close: close,
    setContent: setContent,
    setLoading: setLoading,
    setStep: setStep,
    setLastTriggerSource: setLastTriggerSource,
    showError: showError,
    showSuccess: showSuccess,
    minimizeLauncher: minimizeLauncher,
    expand: expandShell,
    getRoot: getRoot,
    getContentMount: getContentMount,
  };

  window.CartflowWidgetRuntime.Shell = Shell;
})();
