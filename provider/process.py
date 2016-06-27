def monitor_interrupt(work):
    """
    Given a lambda work that takes an arbitrary long time to execute,
    listens for interrupts and gracefully prints an exiting message
    if they happen.
    """
    try:
        work()
    except KeyboardInterrupt:
        print "\nCaught KeyboardInterrupt, shutting down..."
