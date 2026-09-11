"""lineage bridge for missing merge head p2q3r4s5t6u7

Revision ID: p2q3r4s5t6u7
Revises: None
Create Date: 2026-09-11

Reconstructed graph node only. `s1t2u3v4w5x6` merges this revision with
`r4s5t6u7v8w9`, but the file was never in the repo. Intended object was
`movement_snapshots` (model + create_all). No DDL here — do not invent the
lost migration body.
"""
from typing import Sequence, Union

revision: str = "p2q3r4s5t6u7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
