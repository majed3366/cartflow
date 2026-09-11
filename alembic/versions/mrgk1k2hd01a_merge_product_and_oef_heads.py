# -*- coding: utf-8 -*-
"""Merge surviving heads so post-head reconstruction eras have one parent.

Revision ID: mrgk1k2hd01a
Revises: k1l2m3n4o5p6q7, k2l3m4n5o6p7
Create Date: 2026-09-11

No DDL. p2q3 remains a no-op; movement_snapshots is E10 after this merge.
"""
from __future__ import annotations

from typing import Sequence, Union

revision: str = "mrgk1k2hd01a"
down_revision: Union[str, Sequence[str], None] = ("k1l2m3n4o5p6q7", "k2l3m4n5o6p7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
