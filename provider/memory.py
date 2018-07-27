import os
import psutil


def current():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss
