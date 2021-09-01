from queue_worker import QueueWorker
from provider import process, utils


QUEUE_SETTING_NAME = "accepted_submission_queue"


class AcceptedSubmissionQueueWorker(QueueWorker):
    def __init__(
        self, settings, logger=None, identity="accepted_submission_queue_worker"
    ):
        super(AcceptedSubmissionQueueWorker, self).__init__(settings, logger, identity)
        self.input_queue_name = getattr(self.settings, QUEUE_SETTING_NAME, None)


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    queue_worker_object = CleaningQueueWorker(SETTINGS)
    # only start if the queue name is specified in the settings
    if getattr(SETTINGS, QUEUE_SETTING_NAME, None):
        process.monitor_interrupt(lambda flag: queue_worker_object.work(flag))
