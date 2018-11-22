import signal

"""
Provides process-management utilities such as catching signals and interrupts
"""

class Flag:
    def __init__(self):
        self._red = False

    def green(self):
        return not self._red

    def red(self):
        return self._red

    def stop_process(self):
        self._red = True


def monitor_interrupt(work):
    """
    Given a lambda work that takes an arbitrary long time to execute,
    listens for interrupts and gracefully prints an exiting message
    if they happen.

    Exits immediately for Ctrl+C interrupts. Waits for graceful shutdown
    for SIGTERM instead.
    """
    try:
        flag = Flag()
        def signal_handler(signum, _frame):
            print("received signal %s" % signum)
            flag.stop_process()
        signal.signal(signal.SIGTERM, signal_handler)
        work(flag)
    except KeyboardInterrupt:
        print("\ncaught KeyboardInterrupt, shutting down abruptly...")
