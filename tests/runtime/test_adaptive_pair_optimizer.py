from __future__ import annotations

import pandas as pd

from runtime.adaptive_pair_optimizer import add_tf_features


def test_higher_timeframe_features_only_use_closed_child_candles() -> None:
    dates = pd.date_range("2026-01-01", periods=17, freq="15min", tz="UTC")
    close = pd.Series(range(1, 18), dtype=float)
    frame = pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1.0,
        }
    )

    informative = add_tf_features(frame, "4h", "4h")
    completed = informative.loc[
        informative["date"] == pd.Timestamp("2026-01-01 04:00:00", tz="UTC")
    ].iloc[0]

    # The child candle opening at 04:00 closes at 04:15 and must not be
    # visible in the 4h candle that becomes available at 04:00.
    assert completed["close_4h"] == 16.0
