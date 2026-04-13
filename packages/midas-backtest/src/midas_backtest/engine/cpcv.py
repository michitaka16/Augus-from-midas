"""
Combinatorial Purged Cross-Validation (CPCV) — López de Prado.

Generates all combinatorial train/test splits with:
- Purge window: 5 trading days (prevents look-ahead from rolling statistics)
- Embargo window: 2 trading days (prevents leakage from regime hysteresis)

Returns a distribution of Sharpe ratios across all splits,
used to compute Deflated Sharpe and PBO.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CPCVSplit:
    """One train/test split with purge + embargo."""
    train_indices: list[int]
    test_indices: list[int]
    sharpe: float
    total_return: float


@dataclass
class CPCVResult:
    """Aggregate CPCV results."""
    splits: list[CPCVSplit]
    sharpe_distribution: list[float]
    mean_sharpe: float
    std_sharpe: float
    pbo: float
    n_splits: int


class CPCVEngine:
    """Combinatorial Purged Cross-Validation.

    Divides the time series into N groups, generates all C(N, N/2) train/test
    combinations, and evaluates the strategy on each. Purge and embargo
    windows prevent data leakage.
    """

    def __init__(
        self,
        n_groups: int = 10,
        purge_days: int = 5,
        embargo_days: int = 2,
    ):
        self.n_groups = n_groups
        self.purge_days = purge_days
        self.embargo_days = embargo_days

    def generate_splits(self, n_samples: int) -> list[tuple[list[int], list[int]]]:
        """Generate all combinatorial train/test splits with purge + embargo.

        Divides n_samples into n_groups, selects n_groups/2 for testing,
        remainder for training. Removes purge + embargo samples around
        train/test boundaries.
        """
        group_size = n_samples // self.n_groups
        if group_size < 1:
            logger.warning("cpcv.insufficient_data", n_samples=n_samples, n_groups=self.n_groups)
            return []

        # Assign each sample to a group
        groups = []
        for i in range(self.n_groups):
            start = i * group_size
            end = start + group_size if i < self.n_groups - 1 else n_samples
            groups.append(list(range(start, end)))

        # Generate all C(N, N/2) combinations of test groups
        n_test_groups = self.n_groups // 2
        test_combos = list(itertools.combinations(range(self.n_groups), n_test_groups))

        # Cap at 100 splits to keep computation tractable
        if len(test_combos) > 100:
            rng = np.random.RandomState(42)
            indices = rng.choice(len(test_combos), 100, replace=False)
            test_combos = [test_combos[i] for i in sorted(indices)]

        splits = []
        for test_group_ids in test_combos:
            test_set = set()
            for gid in test_group_ids:
                test_set.update(groups[gid])

            train_set = set(range(n_samples)) - test_set

            # Apply purge: remove train samples within purge_days of any test boundary
            purge_set = set()
            for idx in test_set:
                for offset in range(-self.purge_days, self.purge_days + 1):
                    purge_set.add(idx + offset)
            train_set -= purge_set

            # Apply embargo: remove train samples within embargo_days after test end
            embargo_set = set()
            test_sorted = sorted(test_set)
            if test_sorted:
                test_end = max(test_sorted)
                for offset in range(1, self.embargo_days + 1):
                    embargo_set.add(test_end + offset)
            train_set -= embargo_set

            train_indices = sorted(train_set)
            test_indices = sorted(test_set)

            if len(train_indices) > 0 and len(test_indices) > 0:
                splits.append((train_indices, test_indices))

        logger.info(
            "cpcv.splits_generated",
            n_splits=len(splits),
            n_groups=self.n_groups,
            purge=self.purge_days,
            embargo=self.embargo_days,
        )
        return splits

    async def run(
        self,
        returns: list[float],
        risk_free_rate: float = 0.0,
    ) -> CPCVResult:
        """Run CPCV on a return series.

        For each split, computes the Sharpe ratio on the test set.
        Returns the distribution of Sharpes for PBO and Deflated Sharpe.
        """
        from midas_backtest.metrics.sharpe import sharpe_ratio

        splits_spec = self.generate_splits(len(returns))
        ret_array = np.array(returns)

        splits = []
        sharpes = []

        for train_idx, test_idx in splits_spec:
            test_returns = ret_array[test_idx].tolist()
            if len(test_returns) < 5:
                continue

            sr = sharpe_ratio(test_returns, risk_free_rate)
            total_ret = float(np.prod(1 + np.array(test_returns)) - 1)

            splits.append(CPCVSplit(
                train_indices=train_idx,
                test_indices=test_idx,
                sharpe=round(sr, 4),
                total_return=round(total_ret, 6),
            ))
            sharpes.append(sr)

        if not sharpes:
            return CPCVResult(
                splits=[], sharpe_distribution=[], mean_sharpe=0,
                std_sharpe=0, pbo=1.0, n_splits=0,
            )

        # PBO = fraction of splits with negative OOS Sharpe
        pbo = sum(1 for s in sharpes if s < 0) / len(sharpes)

        result = CPCVResult(
            splits=splits,
            sharpe_distribution=[round(s, 4) for s in sharpes],
            mean_sharpe=round(float(np.mean(sharpes)), 4),
            std_sharpe=round(float(np.std(sharpes)), 4),
            pbo=round(pbo, 4),
            n_splits=len(splits),
        )

        logger.info(
            "cpcv.complete",
            n_splits=result.n_splits,
            mean_sharpe=result.mean_sharpe,
            pbo=result.pbo,
        )
        return result
