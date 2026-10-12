"""Paired significance for before/after comparisons on the same items.

Every comparison in this project is paired: the same 57 problems, or the same 770
MMLU/theory items, scored under two configurations. The right test for a paired binary
outcome is McNemar's, and with the small discordant counts seen here (5 to 30) the
exact binomial form is required — the chi-squared approximation is unreliable below
about 25 discordant pairs.
"""
from __future__ import annotations

from math import comb
from typing import Iterable, Mapping


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value.

    b = items right under A and wrong under B; c = wrong under A, right under B.
    Under the null each discordant item is equally likely to fall either way, so
    min(b, c) is Binomial(b + c, 0.5). Concordant items carry no information.
    Returns 1.0 when there are no discordant items.
    """
    if b < 0 or c < 0:
        raise ValueError("counts must be non-negative")
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(a: Mapping[str, bool], b: Mapping[str, bool], label_a: str = "A",
           label_b: str = "B") -> dict:
    """Compare two configurations scored on the same item ids.

    `a` and `b` map item id -> correct. Only ids present in both are compared, and
    the count of each is reported so a silent mismatch is visible.
    """
    common = sorted(set(a) & set(b))
    if not common:
        raise ValueError("the two runs share no item ids")
    right_to_wrong = sum(1 for i in common if a[i] and not b[i])
    wrong_to_right = sum(1 for i in common if not a[i] and b[i])
    acc_a = sum(a[i] for i in common) / len(common)
    acc_b = sum(b[i] for i in common) / len(common)
    return dict(
        a=label_a, b=label_b, n=len(common),
        only_in_a=len(set(a) - set(b)), only_in_b=len(set(b) - set(a)),
        correct_a=sum(a[i] for i in common), correct_b=sum(b[i] for i in common),
        accuracy_a=round(acc_a, 4), accuracy_b=round(acc_b, 4),
        delta_pp=round(100 * (acc_b - acc_a), 2),
        right_to_wrong=right_to_wrong, wrong_to_right=wrong_to_right,
        discordant=right_to_wrong + wrong_to_right,
        mcnemar_p=round(mcnemar_exact(right_to_wrong, wrong_to_right), 6),
    )


def by_id(items: Iterable[Mapping], key: str = "id", field: str = "correct") -> dict:
    """{id: bool} from a list of per-item records."""
    return {str(r[key]): bool(r[field]) for r in items}
