"""lineage bridge for missing parent m1n2o3p4q5r6

Revision ID: m1n2o3p4q5r6
Revises: None
Create Date: 2026-09-11

Reconstructed graph node only. `n2o3p4q5r6s7` referenced this revision but the
file was never in the repo. No DDL — do not invent historical schema.
"""
from typing import Sequence, Union

revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, Sequence[str], None] = "e0fnd250425a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
