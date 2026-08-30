# Incident history

1. Settings first-load exhausted the shared API pool with concurrent DB-bound reads. Remediated (sequential store-connection + recovery-settings; no Promise.all).
2. Living Store review hit QueuePool timeouts. Review-session was a victim; dashboard startup fan-out was the cause.
3. Merchant V2 startup fan-out remediated at `58a82f3`: inactive surface startup requests = 0. Controlled production validation passed.
4. QueuePool exhaustion returned during normal live/mobile usage.

Conclusion: this is no longer a single-route bug. The platform lacked guarantees that connections are acquired late, held briefly, released before wait, and bounded per surface/merchant.
