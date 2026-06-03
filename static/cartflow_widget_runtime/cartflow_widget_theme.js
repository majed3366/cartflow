/**
 * Merchant-color theme tokens for storefront widget runtime.
 * Single source: merchant widget_primary_color → CSS vars + style helpers.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var LEGACY_PURPLE_PATTERNS = [
    /6366f1/i,
    /4f46e5/i,
    /4338ca/i,
    /312e81/i,
    /1e1b4b/i,
    /6c5ce7/i,
    /99,\s*102,\s*241/i,
    /\bindigo\b/i,
    /\bpurple\b/i,
    /\bviolet\b/i,
  ];

  var _tokens = null;
  var _merchantColor = null;
  var _loggedTheme = false;

  function parseHex6(hex) {
    if (!hex) {
      return null;
    }
    var s = String(hex).trim().replace(/^#/, "");
    if (s.length === 3) {
      s =
        s.charAt(0) +
        s.charAt(0) +
        s.charAt(1) +
        s.charAt(1) +
        s.charAt(2) +
        s.charAt(2);
    }
    if (!/^[0-9A-Fa-f]{6}$/.test(s)) {
      return null;
    }
    return {
      r: parseInt(s.slice(0, 2), 16),
      g: parseInt(s.slice(2, 4), 16),
      b: parseInt(s.slice(4, 6), 16),
      hex: ("#" + s).toUpperCase(),
    };
  }

  function hexByte(n) {
    var s = Math.max(0, Math.min(255, Math.round(n))).toString(16);
    return s.length < 2 ? "0" + s : s;
  }

  function rgbToHex(rgb) {
    if (!rgb) {
      return null;
    }
    return ("#" + hexByte(rgb.r) + hexByte(rgb.g) + hexByte(rgb.b)).toUpperCase();
  }

  function darkenHex(hex, amount) {
    var rgb = parseHex6(hex);
    if (!rgb) {
      return hex;
    }
    var f = 1 - (amount == null ? 0.15 : amount);
    return rgbToHex({ r: rgb.r * f, g: rgb.g * f, b: rgb.b * f });
  }

  function lightenHex(hex, amount) {
    var rgb = parseHex6(hex);
    if (!rgb) {
      return hex;
    }
    var f = amount == null ? 0.15 : amount;
    return rgbToHex({
      r: rgb.r + (255 - rgb.r) * f,
      g: rgb.g + (255 - rgb.g) * f,
      b: rgb.b + (255 - rgb.b) * f,
    });
  }

  function mixHex(a, b, weightB) {
    var ra = parseHex6(a);
    var rb = parseHex6(b);
    if (!ra || !rb) {
      return a || b;
    }
    var w = weightB == null ? 0.5 : weightB;
    return rgbToHex({
      r: ra.r * (1 - w) + rb.r * w,
      g: ra.g * (1 - w) + rb.g * w,
      b: ra.b * (1 - w) + rb.b * w,
    });
  }

  function rgbaFromHex(hex, alpha) {
    var rgb = parseHex6(hex);
    if (!rgb) {
      return "rgba(0,0,0," + (alpha == null ? 1 : alpha) + ")";
    }
    return (
      "rgba(" +
      rgb.r +
      "," +
      rgb.g +
      "," +
      rgb.b +
      "," +
      (alpha == null ? 1 : alpha) +
      ")"
    );
  }

  function merchantPrimaryHex() {
    try {
      if (Cf.Config && typeof Cf.Config.merchant === "function") {
        var c = Cf.Config.merchant().widget_primary_color;
        if (typeof c === "string" && c.trim()) {
          return String(c).trim();
        }
      }
    } catch (eM) {}
    return null;
  }

  function merchantColorIsActive() {
    try {
      if (Cf.State && Cf.State.internals && Cf.State.internals.v2MerchantConfigResolved) {
        return !!merchantPrimaryHex();
      }
    } catch (eMc) {}
    return false;
  }

  function resolvedPrimary(primaryHex) {
    return primaryHex || merchantPrimaryHex() || "#888888";
  }

  function buildTokens(primaryHex) {
    var primary = resolvedPrimary(primaryHex);
    var rgb = parseHex6(primary);
    if (!rgb) {
      primary = "#888888";
      rgb = parseHex6(primary);
    }
    var primaryDark = darkenHex(primary, 0.2);
    var primaryLight = lightenHex(primary, 0.24);
    var surfaceDeep = mixHex(primaryDark, "#050505", 0.55);
    var surfaceMid = mixHex(primary, "#0c0c0c", 0.78);
    var surfaceLight = mixHex(primaryLight, "#141414", 0.62);
    var border = rgbaFromHex(primary, 0.48);
    var borderSoft = rgbaFromHex(primary, 0.28);
    var hover = lightenHex(primary, 0.1);
    var focus = rgbaFromHex(primaryLight, 0.72);
    var inputBg = rgbaFromHex(primaryDark, 0.42);
    var overlayBg = rgbaFromHex(primaryDark, 0.55);
    var titleColor = lightenHex(primary, 0.42);
    var textOnPrimary = "#FAFAFA";
    var secondaryBg = rgbaFromHex(primary, 0.12);
    var secondaryBorder = rgbaFromHex(primary, 0.32);
    var ghostBorder = rgbaFromHex(primaryLight, 0.26);
    var shellGradient =
      "linear-gradient(165deg," +
      surfaceDeep +
      " 0%," +
      surfaceMid +
      " 48%," +
      mixHex(primaryDark, "#080808", 0.65) +
      " 100%)";
    var launcherGradient =
      "linear-gradient(165deg," +
      rgbaFromHex(primary, 0.35) +
      " 0%," +
      mixHex(primaryDark, "#0a0a0a", 0.7) +
      " 55%," +
      surfaceDeep +
      " 100%)";
    var buttonGradient =
      "linear-gradient(180deg," + primary + " 0%," + primaryDark + " 100%)";
    var buttonHoverGradient =
      "linear-gradient(180deg," + hover + " 0%," + primary + " 100%)";
    var chromeBar = primary;
    var focusRing = "0 0 0 2px " + focus;
    var shadowShell =
      "0 18px 48px " + rgbaFromHex(primaryDark, 0.55) + ", inset 0 1px 0 rgba(255,255,255,.08)";
    var shadowLauncher = "0 4px 14px " + rgbaFromHex(primaryDark, 0.45);

    return {
      merchant_color: primary,
      primary: primary,
      primaryDark: primaryDark,
      primaryLight: primaryLight,
      surface: surfaceMid,
      surfaceDeep: surfaceDeep,
      surfaceLight: surfaceLight,
      border: border,
      borderSoft: borderSoft,
      hover: hover,
      focus: focus,
      inputBg: inputBg,
      overlayBg: overlayBg,
      titleColor: titleColor,
      textOnPrimary: textOnPrimary,
      secondaryBg: secondaryBg,
      secondaryBorder: secondaryBorder,
      ghostBorder: ghostBorder,
      shellGradient: shellGradient,
      launcherGradient: launcherGradient,
      buttonGradient: buttonGradient,
      buttonHoverGradient: buttonHoverGradient,
      chromeBar: chromeBar,
      focusRing: focusRing,
      shadowShell: shadowShell,
      shadowLauncher: shadowLauncher,
      cssVars: {
        "--cf-primary": primary,
        "--cf-primary-dark": primaryDark,
        "--cf-primary-light": primaryLight,
        "--cf-surface": surfaceMid,
        "--cf-border": border,
        "--cf-hover": hover,
        "--cf-focus": focus,
      },
    };
  }

  function refresh(primaryHex) {
    _merchantColor = merchantPrimaryHex();
    _tokens = buildTokens(primaryHex);
    logThemeTokens();
    auditLegacyPurple();
    return _tokens;
  }

  function tokens() {
    if (!_tokens) {
      refresh(null);
    }
    return _tokens;
  }

  function applyCssVars(el) {
    if (!el) {
      return;
    }
    var t = tokens();
    var vars = t.cssVars;
    var k;
    try {
      for (k in vars) {
        if (Object.prototype.hasOwnProperty.call(vars, k)) {
          el.style.setProperty(k, vars[k]);
        }
      }
    } catch (eSet) {}
  }

  function shellBackground() {
    return tokens().shellGradient;
  }

  function launcherBackground() {
    return tokens().launcherGradient;
  }

  function shellBorder(alpha) {
    return rgbaFromHex(tokens().primary, alpha == null ? 0.48 : alpha);
  }

  function primaryButtonGradient() {
    return tokens().buttonGradient;
  }

  function inputBorderCss() {
    return "1px solid " + tokens().borderSoft;
  }

  function inputFieldCss() {
    var t = tokens();
    return (
      "width:100%;box-sizing:border-box;border-radius:9px;border:" +
      inputBorderCss() +
      ";background:" +
      t.inputBg +
      ";padding:9px 10px;font:inherit;font-size:14px;color:#f8fafc;outline:none;"
    );
  }

  function inputFieldCssCompact() {
    var t = tokens();
    return (
      "width:100%;box-sizing:border-box;border-radius:9px;border:" +
      inputBorderCss() +
      ";background:" +
      t.inputBg +
      ";padding:8px;margin-bottom:8px;font:inherit;color:#f8fafc;"
    );
  }

  function primaryButtonCss() {
    var t = tokens();
    return (
      "cursor:pointer;display:inline-flex;align-items:center;justify-content:center;text-align:center;border-radius:9px;" +
      "background:" +
      t.buttonGradient +
      ";color:" +
      t.textOnPrimary +
      ";width:100%;box-sizing:border-box;" +
      "padding:9px 10px;line-height:1.35;font-weight:600;font-size:13px;" +
      "border:1px solid " +
      rgbaFromHex(t.primaryLight, 0.35) +
      ";box-shadow:0 1px 0 rgba(255,255,255,.12) inset;"
    );
  }

  function secondaryButtonCss() {
    var t = tokens();
    return (
      "cursor:pointer;display:inline-flex;align-items:center;justify-content:center;text-align:center;border-radius:9px;" +
      "background:" +
      t.secondaryBg +
      ";color:#f1f5f9;width:100%;box-sizing:border-box;" +
      "padding:9px 10px;line-height:1.35;font-weight:600;font-size:13px;" +
      "border:1px solid " +
      t.secondaryBorder +
      ";"
    );
  }

  function ghostButtonCss() {
    var t = tokens();
    return (
      "margin-top:6px;border:1px solid " +
      t.ghostBorder +
      ";cursor:pointer;border-radius:9px;" +
      "background:" +
      t.secondaryBg +
      ";color:rgba(241,245,249,.92);width:100%;padding:8px 10px;font-weight:600;font-size:12px;"
    );
  }

  function textPrimaryCss(extra) {
    return "margin:0;color:rgba(248,250,252,.96);" + (extra || "");
  }

  function textMutedCss(extra) {
    var t = tokens();
    return "margin:0;color:" + rgbaFromHex(t.primaryLight, 0.82) + ";" + (extra || "");
  }

  function titleCss() {
    var t = tokens();
    return "font-weight:700;font-size:13px;color:" + t.titleColor + ";letter-spacing:.01em;";
  }

  function closeButtonCss() {
    var t = tokens();
    return (
      "border:0;background:transparent;color:" +
      rgbaFromHex(t.primaryLight, 0.82) +
      ";cursor:pointer;font-size:20px;line-height:1;padding:2px 6px;border-radius:8px;"
    );
  }

  function loadingOverlayCss() {
    var t = tokens();
    return (
      "display:none;position:absolute;left:0;right:0;top:0;bottom:0;align-items:center;justify-content:center;" +
      "flex-direction:row;background:" +
      t.overlayBg +
      ";border-radius:10px;z-index:4;font-size:12px;color:#f1f5f9;"
    );
  }

  function footerCss() {
    var t = tokens();
    return (
      "margin-top:8px;min-height:0;font-size:12px;line-height:1.35;color:" +
      rgbaFromHex(t.primaryLight, 0.88) +
      ";display:none;"
    );
  }

  function launcherChipCss() {
    var t = tokens();
    return "cursor:pointer;color:" + t.textOnPrimary + ";font-size:17px;font-weight:700;line-height:1;padding:0;";
  }

  function containsLegacyPurple(str) {
    if (!str) {
      return false;
    }
    var s = String(str);
    var i;
    for (i = 0; i < LEGACY_PURPLE_PATTERNS.length; i++) {
      if (LEGACY_PURPLE_PATTERNS[i].test(s)) {
        return true;
      }
    }
    return false;
  }

  function auditLegacyPurple(root) {
    var found = 0;
    try {
      if (!root && Cf.Shell && typeof Cf.Shell.getRoot === "function") {
        root = Cf.Shell.getRoot();
      }
      if (root) {
        var nodes = root.querySelectorAll("*");
        var i;
        for (i = 0; i < nodes.length; i++) {
          var el = nodes[i];
          if (el.getAttribute && el.getAttribute("style")) {
            if (containsLegacyPurple(el.getAttribute("style"))) {
              found += 1;
            }
          }
          try {
            if (el.style && el.style.cssText && containsLegacyPurple(el.style.cssText)) {
              found += 1;
            }
          } catch (eSt) {}
        }
        if (root.getAttribute && root.getAttribute("style")) {
          if (containsLegacyPurple(root.getAttribute("style"))) {
            found += 1;
          }
        }
      }
    } catch (eAud) {}
    try {
      console.log("[CF LEGACY PURPLE CHECK]", { legacy_tokens_found: found });
    } catch (eLog) {}
    return found;
  }

  function logThemeTokens() {
    var t = tokens();
    try {
      console.log("[CF THEME TOKENS]", {
        merchant_color: _merchantColor || t.merchant_color,
        primary: t.primary,
        surface: t.surface,
        border: t.border,
        hover: t.hover,
      });
    } catch (eLt) {}
    _loggedTheme = true;
  }

  var Theme = {
    refresh: refresh,
    tokens: tokens,
    applyCssVars: applyCssVars,
    resolvedPrimary: resolvedPrimary,
    merchantColorIsActive: merchantColorIsActive,
    merchantPrimaryHex: merchantPrimaryHex,
    shellBackground: shellBackground,
    launcherBackground: launcherBackground,
    shellBorder: shellBorder,
    primaryButtonGradient: primaryButtonGradient,
    inputBorderCss: inputBorderCss,
    inputFieldCss: inputFieldCss,
    inputFieldCssCompact: inputFieldCssCompact,
    primaryButtonCss: primaryButtonCss,
    secondaryButtonCss: secondaryButtonCss,
    ghostButtonCss: ghostButtonCss,
    textPrimaryCss: textPrimaryCss,
    textMutedCss: textMutedCss,
    titleCss: titleCss,
    closeButtonCss: closeButtonCss,
    loadingOverlayCss: loadingOverlayCss,
    footerCss: footerCss,
    launcherChipCss: launcherChipCss,
    rgbaFromHex: rgbaFromHex,
    darkenHex: darkenHex,
    lightenHex: lightenHex,
    auditLegacyPurple: auditLegacyPurple,
    containsLegacyPurple: containsLegacyPurple,
  };

  Cf.Theme = Theme;
  refresh(null);
})();
