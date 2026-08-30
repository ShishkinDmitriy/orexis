"""The reactive contract, held: one thread, in order, a handle for the enqueuer, and a loop
that outlives any one failure. Each was broken once and seen to fail before it was trusted."""

from __future__ import annotations

import threading

import pytest

from orexis_reactive.loop import Loop


def test_work_runs_in_order_on_one_thread_and_the_handle_resolves_elsewhere():
    loop = Loop("test")
    seen: list[tuple[int, threading.Thread]] = []
    futures = [loop.submit(lambda i=i: seen.append((i, threading.current_thread())) or i)
               for i in range(5)]
    assert [f.result(timeout=5) for f in futures] == [0, 1, 2, 3, 4]
    assert [i for i, _ in seen] == [0, 1, 2, 3, 4], "FIFO, or a deadline lands before a tick"
    threads = {t for _, t in seen}
    assert len(threads) == 1 and threading.current_thread() not in threads, \
        "every item ran on the loop's own thread, never the submitter's"
    assert not loop.is_current(), "the submitter is not the loop"
    assert loop.submit(loop.is_current).result(timeout=5) is True, "an item on the loop IS"
    loop.stop()


def test_a_failing_item_does_not_stop_the_loop():
    loop = Loop("test")

    def boom():
        raise ValueError("one item's fault")

    failed = loop.submit(boom)
    with pytest.raises(ValueError):
        failed.result(timeout=5)
    assert loop.submit(lambda: "still here").result(timeout=5) == "still here"
    loop.stop()


def test_a_stopped_loop_refuses_rather_than_swallowing():
    loop = Loop("test")
    loop.submit(lambda: None).result(timeout=5)
    loop.stop()
    with pytest.raises(RuntimeError):
        loop.submit(lambda: None)
