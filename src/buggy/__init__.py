# SPDX-License-Identifier: AGPL-3.0-or-later
"""buggy — where, when and why a test suite went red, from evidence and two integer laws. No model.

WHERE ranks the lines the failing test executed by the CAUSE law; the OMISSION law says where missing
code belongs; WHEN bisects the commit that introduced the failure with the failing test carried back
through history; WHY traces the failing test against a passing neighbour to the first divergence."""
__version__ = "0.1.0"
