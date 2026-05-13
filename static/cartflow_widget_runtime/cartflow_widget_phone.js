/**
 * Phone normalization + bundled reason POST (single API hop after user confirms).
 */
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime || {};

  function deferAfterReasonCapture() {
    var pcm =
      Cf.Config && Cf.Config.phoneCaptureMode
        ? Cf.Config.phoneCaptureMode()
        : "after_reason";
    if (pcm !== "after_reason") {
      return false;
    }
    if (Cf.State.sessionConvertedBlock()) {
      return false;
    }
    try {
      if (window.cartflowState && window.cartflowState.isVip === true) {
        return false;
      }
    } catch (eV) {}
    return Cf.State && Cf.State.hasValidStoredPhone ? !Cf.State.hasValidStoredPhone() : false;
  }

  function postReasonMerged(pendingPayload, phoneNorm, subHint, textHint, reasonKeyGuess) {
    var body = {};
    var pk;
    for (pk in pendingPayload || {}) {
      if (Object.prototype.hasOwnProperty.call(pendingPayload, pk)) {
        body[pk] = pendingPayload[pk];
      }
    }
    body.customer_phone = phoneNorm;
    if (!body.reason) {
      body.reason = reasonKeyGuess || "other";
    }
    if (subHint != null && String(subHint).trim() && body.sub_category == null) {
      body.sub_category = String(subHint).trim();
    }
    if (textHint != null && String(textHint).trim() && body.custom_text == null) {
      body.custom_text = String(textHint).trim();
    }
    try {
      console.log("[CF REASON_PHONE_SAVE_START V2]", { reason_key: String(body.reason) });
    } catch (eL) {}
    return Cf.Api.postReason(body).then(function (j) {
      if (!Cf.Api.reasonPostOk(j)) {
        try {
          console.log("[CF REASON_PHONE_SAVE_FAILED V2]", { trace: "server_reject" });
        } catch (eF) {}
        return Promise.reject(new Error("reason_post_failed"));
      }
      try {
        localStorage.setItem(Cf.State.LS_CUSTOMER_PHONE, phoneNorm);
      } catch (eLs) {}
      try {
        console.log("[CF REASON_PHONE_SAVE_SUCCESS V2]");
      } catch (eOk) {}
      return j;
    });
  }

  window.CartflowWidgetRuntime = Cf;
  window.CartflowWidgetRuntime.Phone = {
    deferAfterReasonCapture: deferAfterReasonCapture,
    postReasonMerged: postReasonMerged,
  };
})();
