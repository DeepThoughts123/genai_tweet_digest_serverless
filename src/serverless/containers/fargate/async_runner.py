"""Async entry-point for the Fargate classifier container.

Usage (inside container):

    python -m fargate.async_runner
"""
from __future__ import annotations

import asyncio
import logging
import signal
import contextlib
from typing import Optional

from shared import env

from .classifier_service import ClassifierService

_LOG = logging.getLogger("async_runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


async def _run_loop(service: ClassifierService, stop_event: asyncio.Event, idle_sleep: float = 1.0):
    """Background loop that processes SQS batches until *stop_event* is set."""
    while not stop_event.is_set():
        processed = await asyncio.to_thread(service.process_once)
        if processed == 0:
            # No work, back off a bit to avoid busy loop
            await asyncio.sleep(idle_sleep)


async def main() -> None:  # noqa: D401
    """Program entry point – build service from env and run forever."""
    service = ClassifierService.from_env()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def _handle_sig(*_):  # noqa: D401
        _LOG.info("Received shutdown signal, stopping loop …")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(ValueError):
            loop.add_signal_handler(sig, _handle_sig)

    _LOG.info("Classifier service starting – batch size=%d", service._BATCH_SIZE)  # noqa: SLF001
    await _run_loop(service, stop_event)
    _LOG.info("Classifier service stopped.")


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass 