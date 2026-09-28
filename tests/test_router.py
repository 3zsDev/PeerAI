import threading
import time

from peerai.ai.fake import FakeAiClient
from peerai.ai.router import Router, classify
from peerai.events import AiResult, Rect, Target


def mk(text="", **kw):
    return Target(bbox=Rect(0, 0, 200, 100), text=text, app_name="app", **kw)


def test_classify_kinds():
    assert classify(mk("What is the capital of Australia?")) == "question"
    assert classify(mk("def f(x):\n    return x + 1\n\nclass A:\n    pass\n")) == "code"
    assert classify(mk("The mitochondrion is the powerhouse of the cell. It makes ATP.")) == "text"
    assert classify(mk("", image_png=b"png")) == "image"
    assert classify(mk("Save", kind_hint="ui_element")) == "ui_element"
    assert classify(mk("")) == "unknown"


def collect():
    results = []
    done = threading.Event()

    def emit(r: AiResult):
        results.append(r)
        if r.done:
            done.set()

    return results, done, emit


def test_streams_then_caches():
    client = FakeAiClient()
    results, done, emit = collect()
    router = Router(client, client, emit)
    t = mk("What is the capital of Australia?")
    router.submit(t)
    assert done.wait(2)
    assert results[-1].done and results[-1].text.startswith("[question]")
    assert len(client.calls) == 1

    results.clear()
    router.submit(t)  # cached: emitted synchronously, no second model call
    assert results and results[0].done
    assert len(client.calls) == 1


def test_newer_target_cancels_older():
    client = FakeAiClient(delay_s=0.05)
    results, done, emit = collect()
    router = Router(client, client, emit)
    a, b = mk("first passage about something long enough to be text"), mk("second passage about something else entirely")
    router.submit(a)
    time.sleep(0.08)
    router.submit(b)
    assert done.wait(3)
    router.join(2)
    finished = [r for r in results if r.done]
    assert [r.target_hash for r in finished] == [b.hash]
    assert router.cached(a.hash) is None
    assert router.cached(b.hash) is not None


def test_image_without_vision_client_reports_error():
    results, done, emit = collect()
    router = Router(FakeAiClient(), None, emit)
    router.submit(mk("", image_png=b"png"))
    assert done.wait(2)
    assert results[-1].error
