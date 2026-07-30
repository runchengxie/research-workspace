"""style_factors computation helpers.

The new-factor helpers and the PIT SW-L1 industry merge live in dedicated
modules so the parent ``factor_calc`` stays below the large-file threshold and
no single function exceeds the complexity ceiling.  Public names are re-exported
here for convenience.
"""

from __future__ import annotations

from ._aux import _assign_aux_panel, _merge_aux
from ._neutralize import merge_sw_industry_pit
from ._new_factors import add_new_factors

__all__ = [
    "add_new_factors",
    "merge_sw_industry_pit",
    "_merge_aux",
    "_assign_aux_panel",
]
