"""
A single background thread with one persistent asyncio event loop is used for all WinRT calls.

Previously, each call created a new thread and event loop, 
causing repeated COM/WinRT initialization and teardown. 

This happened frequently in the session polling loop and led to 
unnecessary native resource churn and gradual memory growth.

The fix reuses one thread and event loop for the app’s lifetime, 
keeping WinRT calls off the Tkinter main thread without repeatedly recreating COM resources.
"""

import asyncio
import threading


class AsyncWorker:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro, callback=None):
        """
        Schedule a coroutine on the persistent worker loop.

        If a callback is provided, it receives the completed Future. 
        Use future.result() to get the result or re-raise any exception.

        The callback runs on the worker thread, not the Tk main thread. 
        UI updates must be sent back using root.after(0, ...).
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if callback:
            future.add_done_callback(callback)
        return future


# One shared instance for the whole app.
_worker = AsyncWorker()


def run_async(coro, callback=None):
    """Convenience wrapper around the shared AsyncWorker instance."""
    return _worker.run(coro, callback)