import asyncio

import pytest

from yahir_reusable_bot.channels import Channel, DeliveryResult, ReportingChannel
from yahir_reusable_bot.scheduler.engine import SchedulerEngine


class Fixed(Channel):
    name = "fixed"

    def __init__(self, result=None, exc=None):
        self.result, self.exc = result, exc

    def send(self, text):
        if self.exc:
            raise self.exc
        return self.result


def test_reporting_channel_forwards_and_observes():
    seen = []
    ch = ReportingChannel(Fixed(DeliveryResult(ok=False, detail="HTTP 503")), seen.append)
    assert ch.send("hi") == DeliveryResult(ok=False, detail="HTTP 503")
    assert seen == [DeliveryResult(ok=False, detail="HTTP 503")] and ch.name == "fixed"


def test_reporting_channel_records_a_raise_then_reraises():
    seen = []
    ch = ReportingChannel(Fixed(exc=RuntimeError("boom")), seen.append)
    with pytest.raises(RuntimeError):
        ch.send("hi")
    assert seen == [DeliveryResult(ok=False, detail="RuntimeError: boom")]


def test_observer_failure_never_breaks_delivery():
    def bad(_):
        raise ValueError("observer bug")
    assert ReportingChannel(Fixed(DeliveryResult(ok=True)), bad).send("hi").ok


class FakeScheduler:
    def __init__(self):
        self.jobs = {}

    def add_job(self, func, **kw):
        self.jobs[kw["id"]] = (func, kw)


def test_engine_reports_job_results_and_reraises():
    seen = []
    sched = FakeScheduler()
    eng = SchedulerEngine(sched, on_job_result=lambda n, ok, err: seen.append((n, ok, err)))
    eng.register("ok-job", trigger="t", callback=lambda x: x * 2, args=[21])
    eng.register("bad-job", trigger="t", callback=lambda: 1 / 0)
    func, kw = sched.jobs["ok-job"]
    assert func(*kw["args"]) == 42
    with pytest.raises(ZeroDivisionError):
        sched.jobs["bad-job"][0]()
    assert seen == [("ok-job", True, None), ("bad-job", False, "ZeroDivisionError: division by zero")]


def test_engine_reports_async_jobs():
    seen = []
    sched = FakeScheduler()

    async def cb():
        return "done"

    SchedulerEngine(sched, on_job_result=lambda n, ok, err: seen.append((n, ok))).register("a", trigger="t", callback=cb)
    assert asyncio.run(sched.jobs["a"][0]()) == "done" and seen == [("a", True)]


def test_engine_without_observer_passes_callback_through_untouched():
    sched = FakeScheduler()

    def cb():
        return None

    SchedulerEngine(sched).register("j", trigger="t", callback=cb)
    assert sched.jobs["j"][0] is cb


def test_build_client_reports_connection_events():
    import discord

    from yahir_reusable_bot.discord.gateway import build_client

    async def on_message(_):
        return None

    seen = []
    client = build_client(on_message=on_message, view=discord.ui.View(timeout=None), on_connection=seen.append)

    async def fire():
        await client.on_ready()
        await client.on_disconnect()
        await client.on_resumed()

    asyncio.run(fire())
    assert seen == [True, False, True]


class Rich(Channel):
    """A channel with an extra delivery method and a plain attribute, like an app channel."""
    name = "rich"
    marker = "inner-attr"

    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.calls = result, exc, []

    def send(self, text):
        return DeliveryResult(ok=True)

    def send_briefing(self, text, extra):
        self.calls.append((text, extra))
        if self.exc:
            raise self.exc
        return self.result

    def describe(self):
        return "plain method"


def test_record_names_extra_delivery_methods():
    seen = []
    inner = Rich(DeliveryResult(ok=False, detail="HTTP 500"))
    ch = ReportingChannel(inner, seen.append, record=("send_briefing",))
    assert ch.send_briefing("hi", extra=1) == DeliveryResult(ok=False, detail="HTTP 500")
    assert inner.calls == [("hi", 1)] and seen == [DeliveryResult(ok=False, detail="HTTP 500")]


def test_recorded_method_reports_a_raise_then_reraises():
    seen = []
    ch = ReportingChannel(Rich(exc=TimeoutError("slow")), seen.append, record=("send_briefing",))
    with pytest.raises(TimeoutError):
        ch.send_briefing("hi", None)
    assert seen == [DeliveryResult(ok=False, detail="TimeoutError: slow")]


def test_other_attributes_pass_through_unrecorded():
    seen = []
    ch = ReportingChannel(Rich(), seen.append)
    assert ch.describe() == "plain method" and ch.marker == "inner-attr"
    assert seen == []
    with pytest.raises(AttributeError):
        ch.no_such_attribute


def test_record_rejects_names_the_inner_channel_lacks():
    with pytest.raises(AttributeError, match="send_nothing"):
        ReportingChannel(Rich(), lambda r: None, record=("send_nothing",))
