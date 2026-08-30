/* Controlled request-map harness — mocked fetch, no live pool. */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..", "..", "..");

function loadSource(rel) {
  return fs.readFileSync(path.join(ROOT, rel), "utf8");
}

function makeEl(spec) {
  const attrs = Object.assign({}, spec.attrs || {});
  if (spec.id) attrs.id = spec.id;
  if (spec["data-cf2-page"]) attrs["data-cf2-page"] = spec["data-cf2-page"];
  const listeners = {};
  const el = {
    id: spec.id || "",
    attrs: attrs,
    hidden: !!spec.hidden,
    innerHTML: spec.innerHTML || "",
    textContent: "",
    className: spec.className || "",
    style: {},
    children: spec.children || [],
    classList: {
      add: function (c) {
        if ((" " + el.className + " ").indexOf(" " + c + " ") < 0) {
          el.className = (el.className + " " + c).trim();
        }
      },
      remove: function (c) {
        el.className = el.className
          .split(/\s+/)
          .filter(function (x) {
            return x && x !== c;
          })
          .join(" ");
      },
      toggle: function (c, on) {
        if (on === undefined) on = (" " + el.className + " ").indexOf(" " + c + " ") < 0;
        if (on) el.classList.add(c);
        else el.classList.remove(c);
        return on;
      },
      contains: function (c) {
        return (" " + el.className + " ").indexOf(" " + c + " ") >= 0;
      },
    },
    getAttribute: function (k) {
      return Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null;
    },
    setAttribute: function (k, v) {
      el.attrs[k] = String(v);
    },
    removeAttribute: function (k) {
      delete el.attrs[k];
    },
    addEventListener: function (t, fn) {
      (listeners[t] = listeners[t] || []).push(fn);
    },
    querySelector: function (sel) {
      return queryIn(el, sel);
    },
    querySelectorAll: function (sel) {
      return queryAllIn(el, sel);
    },
    closest: function () {
      return null;
    },
    contains: function () {
      return false;
    },
  };
  return el;
}

function queryIn(root, sel) {
  const all = queryAllIn(root, sel);
  return all[0] || null;
}

function queryAllIn(root, sel) {
  const out = [];
  function walk(node) {
    if (!node || node === root) {
      (node.children || []).forEach(walk);
      return;
    }
    if (matchSel(node, sel)) out.push(node);
    (node.children || []).forEach(walk);
  }
  walk(root);
  return out;
}

function matchSel(el, sel) {
  if (sel.charAt(0) === "#") return el.id === sel.slice(1);
  if (sel.charAt(0) === ".") {
    return (" " + (el.className || "") + " ").indexOf(" " + sel.slice(1) + " ") >= 0;
  }
  if (sel.indexOf("[data-cf2-page]") === 0) return !!el.getAttribute("data-cf2-page");
  if (sel.indexOf("[data-cf2-nav]") === 0) return !!el.getAttribute("data-cf2-nav");
  if (sel.indexOf("[data-cf2-ctx-item]") === 0) return !!el.getAttribute("data-cf2-ctx-item");
  if (sel.indexOf("[data-cf2-util=") === 0) return el.getAttribute("data-cf2-util") === "settings";
  if (sel === "body") return el.id === "__body";
  return false;
}

function createDocument() {
  const pages = {
    home: makeEl({
      className: "cf2-page is-active",
      attrs: { "data-cf2-page": "home" },
      children: [makeEl({ id: "cf2-home-root", innerHTML: '<p class="cf2-loading"></p>' })],
    }),
    workspace: makeEl({
      className: "cf2-page",
      hidden: true,
      attrs: { "data-cf2-page": "workspace" },
      children: [makeEl({ id: "cf2-workspace-root" })],
    }),
    carts: makeEl({
      className: "cf2-page",
      hidden: true,
      attrs: { "data-cf2-page": "carts" },
      children: [makeEl({ id: "cf2-carts-root" })],
    }),
    comms: makeEl({
      className: "cf2-page",
      hidden: true,
      attrs: { "data-cf2-page": "comms" },
      children: [makeEl({ id: "cf2-comms-root" })],
    }),
    settings: makeEl({
      className: "cf2-page",
      hidden: true,
      attrs: { "data-cf2-page": "settings" },
      children: [
        makeEl({
          id: "cf2-settings-root",
          className: "cf2-settings",
          children: [
            makeEl({ id: "cf2-settings-list" }),
            makeEl({ id: "cf2-settings-needs" }),
            makeEl({ id: "cf2-settings-detail-empty" }),
            makeEl({ id: "cf2-settings-back" }),
          ],
        }),
      ],
    }),
  };
  const byId = {
    "cf2-home-root": pages.home.children[0],
    "cf2-workspace-root": pages.workspace.children[0],
    "cf2-carts-root": pages.carts.children[0],
    "cf2-comms-root": pages.comms.children[0],
    "cf2-settings-root": pages.settings.children[0],
    "cf2-settings-list": pages.settings.children[0].children[0],
    "cf2-settings-needs": pages.settings.children[0].children[1],
    "cf2-settings-detail-empty": pages.settings.children[0].children[2],
    "cf2-settings-back": pages.settings.children[0].children[3],
    "cf2-nav": makeEl({ id: "cf2-nav" }),
    "cf2-shell": makeEl({ id: "cf2-shell", attrs: { "data-cf2-ctx": "off" } }),
    "cf2-ctx": makeEl({ id: "cf2-ctx", hidden: true }),
    "cf2-ctx-handle": makeEl({ id: "cf2-ctx-handle", hidden: true }),
    "cf2-ctx-backdrop": makeEl({ id: "cf2-ctx-backdrop", hidden: true }),
    "cf2-menu-btn": makeEl({ id: "cf2-menu-btn" }),
    "cf2-mobile-account": makeEl({ id: "cf2-mobile-account" }),
    "cf2-account-btn": makeEl({ id: "cf2-account-btn" }),
    "cf2-drawer": makeEl({ id: "cf2-drawer" }),
    "cf2-drawer-backdrop": makeEl({ className: "cf2-drawer-backdrop" }),
    "cf2-brand": makeEl({ id: "cf2-brand", className: "cf2-brand" }),
  };
  const allPages = [pages.home, pages.workspace, pages.carts, pages.comms, pages.settings];
  const body = makeEl({
    id: "__body",
    attrs: { "data-cf-ui": "v2", "data-cf-merchant-app": "1" },
    children: allPages.concat(Object.values(byId)),
  });
  const docListeners = {};
  const document = {
    readyState: "interactive",
    body: body,
    documentElement: body,
    getElementById: function (id) {
      return byId[id] || null;
    },
    querySelector: function (sel) {
      if (sel === "body") return body;
      if (sel.charAt(0) === "#") return byId[sel.slice(1)] || null;
      if (sel === ".cf2-page") return allPages[0];
      if (sel.indexOf("[data-cf2-util=") === 0) return null;
      return queryIn(body, sel);
    },
    querySelectorAll: function (sel) {
      if (sel === ".cf2-page") return allPages.slice();
      if (sel === "[data-cf2-nav]") return [];
      if (sel === "[data-cf2-ctx-item]") return [];
      return queryAllIn(body, sel);
    },
    addEventListener: function (t, fn) {
      (docListeners[t] = docListeners[t] || []).push(fn);
    },
    _emit: function (t) {
      (docListeners[t] || []).forEach(function (fn) {
        fn();
      });
    },
  };
  return document;
}

function boot(initialHash) {
  const fetches = [];
  let hash = initialHash || "";
  const winListeners = {};
  const document = createDocument();
  const location = {
    get hash() {
      return hash;
    },
    set hash(v) {
      const next = String(v || "");
      const norm = next.charAt(0) === "#" ? next : "#" + next;
      if (norm === hash) return;
      hash = norm;
      process.nextTick(function () {
        (winListeners.hashchange || []).forEach(function (fn) {
          fn();
        });
      });
    },
  };
  const window = {
    document: document,
    location: location,
    fetch: function (url) {
      fetches.push(String(url).split("?")[0]);
      return Promise.resolve({
        ok: true,
        status: 200,
        json: function () {
          return Promise.resolve({
            ok: true,
            home_executive_summary_v1: { enabled: true },
            store_connection: { connected: true, status_label_ar: "مربوط" },
            recovery_delay: 15,
            recovery_attempts: 2,
            merchant_carts_page_rows: [],
            merchant_archived_carts_page_rows: [],
            merchant_message_history_rows: [],
            merchant_followup_rows: [],
            subscription: { current_plan: "starter" },
          });
        },
      });
    },
    addEventListener: function (t, fn) {
      (winListeners[t] = winListeners[t] || []).push(fn);
    },
    matchMedia: function () {
      return { matches: false, addEventListener: function () {}, addListener: function () {} };
    },
    URLSearchParams: URLSearchParams,
  };
  window.window = window;
  window.globalThis = window;
  document.defaultView = window;

  const ctx = vm.createContext(window);
  const files = [
    "static/merchant_ui_v2_home.js",
    "static/merchant_ui_v2_workspace.js",
    "static/merchant_ui_v2_carts.js",
    "static/merchant_ui_v2_comms.js",
    "static/merchant_subscription.js",
    "static/merchant_ui_v2_settings.js",
    "static/merchant_ui_v2_app.js",
  ];
  files.forEach(function (rel) {
    vm.runInContext(loadSource(rel), ctx, { filename: rel });
  });
  document._emit("DOMContentLoaded");

  function go(section) {
    return vm.runInContext("CartFlowUiV2.go(" + JSON.stringify(section) + ")", ctx);
  }

  function flush() {
    return new Promise(function (resolve) {
      setTimeout(resolve, 30);
    });
  }

  return {
    fetches: fetches,
    go: go,
    flush: flush,
    snapshot: function () {
      return fetches.slice();
    },
  };
}

function owned(urls) {
  return urls.filter(function (u) {
    return u.indexOf("/api/") === 0;
  });
}

async function main() {
  const home = boot("#home");
  await home.flush();
  const homeBoot = owned(home.snapshot());

  home.go("workspace");
  await home.flush();
  const afterWorkspace = owned(home.snapshot()).slice(homeBoot.length);

  home.go("carts");
  await home.flush();
  const afterCarts = owned(home.snapshot()).slice(homeBoot.length + afterWorkspace.length);

  home.go("comms");
  await home.flush();
  const afterComms = owned(home.snapshot()).slice(
    homeBoot.length + afterWorkspace.length + afterCarts.length
  );

  home.go("settings");
  await home.flush();
  const afterSettings = owned(home.snapshot()).slice(
    homeBoot.length + afterWorkspace.length + afterCarts.length + afterComms.length
  );

  const beforeReturn = owned(home.snapshot()).length;
  home.go("home");
  await home.flush();
  home.go("workspace");
  await home.flush();
  home.go("carts");
  await home.flush();
  home.go("comms");
  await home.flush();
  home.go("settings");
  await home.flush();
  const returnVisits = owned(home.snapshot()).slice(beforeReturn);

  const wsOnly = boot("#workspace");
  await wsOnly.flush();
  const cartsOnly = boot("#carts");
  await cartsOnly.flush();
  const commsOnly = boot("#communication");
  await commsOnly.flush();
  const settingsOnly = boot("#settings");
  await settingsOnly.flush();

  const viewportA = boot("#home");
  const viewportB = boot("#home");
  await viewportA.flush();
  await viewportB.flush();

  const out = {
    home_active: homeBoot,
    nav_workspace: afterWorkspace,
    nav_carts: afterCarts,
    nav_comms: afterComms,
    nav_settings: afterSettings,
    return_visits: returnVisits,
    workspace_active_only: owned(wsOnly.snapshot()),
    carts_active_only: owned(cartsOnly.snapshot()),
    comms_active_only: owned(commsOnly.snapshot()),
    settings_active_only: owned(settingsOnly.snapshot()),
    two_home_viewports: {
      a: owned(viewportA.snapshot()),
      b: owned(viewportB.snapshot()),
    },
  };
  process.stdout.write(JSON.stringify(out, null, 2));
}

main().catch(function (err) {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
