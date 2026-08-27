# Cart Detail Composition

Required order:

1. Current state
2. Primary action
3. Essential cart/customer context
4. Operational timeline (`ماذا حدث لهذه السلة؟`)
5. Secondary action only when demoted archive is valid

Primary action mapping (unchanged):

| Truth | Key |
|-------|-----|
| automatic | `wait` |
| executable contact | `contact_customer` |
| no-phone / VIP manual | `follow_up_manually` |
| not executable | `review_cart` |
| completed / purchased | `no_action_required` |
| archived | `reopen` |

One primary action. Never two equal CTAs. Never contact a purchased cart.

Purchase terminal: recovery and contact CTAs stay off; timeline remains readable.

VIP: operational chip only. No threshold field.
