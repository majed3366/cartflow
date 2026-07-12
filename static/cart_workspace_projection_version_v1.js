/**
 * Cart Workspace Projection Version Contract V1
 * Paint only when projection_version advances. No business logic.
 */
(function (global) {
  "use strict";

  var ACCEPT = "ACCEPT";
  var STALE_OLDER = "STALE_OLDER";
  var CONFLICT_SAME_VERSION = "CONFLICT_SAME_VERSION";
  var MISSING_PAYLOAD = "MISSING_PAYLOAD";

  function compareProjectionEnvelope(local, incoming) {
    if (!incoming || typeof incoming !== "object") {
      return { decision: MISSING_PAYLOAD, should_paint: false };
    }
    var inVer = Number(incoming.projection_version || 0);
    var inFp = String(incoming.projection_fingerprint || "");
    if (!local) {
      return {
        decision: ACCEPT,
        should_paint: true,
        reason: "first_projection",
        incoming_version: inVer,
      };
    }
    var locVer = Number(local.projection_version || 0);
    var locFp = String(local.projection_fingerprint || "");
    if (inVer < locVer) {
      return {
        decision: STALE_OLDER,
        should_paint: false,
        local_version: locVer,
        incoming_version: inVer,
      };
    }
    if (inVer === locVer) {
      if (inFp && locFp && inFp !== locFp) {
        return {
          decision: CONFLICT_SAME_VERSION,
          should_paint: false,
          local_version: locVer,
          incoming_version: inVer,
        };
      }
      return {
        decision: ACCEPT,
        should_paint: false,
        reason: "same_version_no_repaint",
        local_version: locVer,
        incoming_version: inVer,
      };
    }
    return {
      decision: ACCEPT,
      should_paint: true,
      reason: "version_advanced",
      local_version: locVer,
      incoming_version: inVer,
    };
  }

  global.CartWorkspaceProjectionVersionV1 = {
    compareProjectionEnvelope: compareProjectionEnvelope,
    ACCEPT: ACCEPT,
    STALE_OLDER: STALE_OLDER,
    CONFLICT_SAME_VERSION: CONFLICT_SAME_VERSION,
    MISSING_PAYLOAD: MISSING_PAYLOAD,
  };
})(typeof window !== "undefined" ? window : globalThis);
