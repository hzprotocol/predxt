from predxt.utils.backoff import ExponentialBackoff


def test_exponential_backoff_sequence():
    backoff = ExponentialBackoff(base_seconds=1, max_seconds=60)

    d1 = backoff.next_delay()
    assert 0.9 <= d1 <= 1.1 + 0.1  # jitter allows some slack

    d2 = backoff.next_delay()
    assert d2 >= d1

    # Reset and verify first delay is small again
    backoff.reset()
    d_reset = backoff.next_delay()
    assert d_reset >= 0.9 and d_reset <= 1.1 + 0.1
