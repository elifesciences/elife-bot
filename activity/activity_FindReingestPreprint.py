import json
from provider import github_provider
from activity.objects import Activity


class activity_FindReingestPreprint(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FindReingestPreprint, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FindReingestPreprint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Find preprint versions to be re-ingested and"
            " queue an IngestMeca workflow for each"
        )

        # SQS client
        self.sqs_client = None

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "github_named_user"):
            self.logger.info(
                "%s, github_named_user in settings is missing, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.github_named_user:
            self.logger.info(
                "%s, github_named_user in settings is blank, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS

        # query Github repo for a list of issues assigned to the assignee
        issues = None
        try:
            issues = github_provider.find_github_issues_by_assignee(
                self.settings.github_token,
                self.settings.preprint_issues_repo_name,
                self.settings.github_named_user,
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception getting issues from github by assignee %s: %s"
                % (self.name, self.settings.github_named_user, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        if not issues:
            self.logger.info(
                "%s, no Github issues assigned to %s"
                % (self.name, self.settings.github_named_user)
            )
            return self.ACTIVITY_SUCCESS

        # process issues
        for issue in issues:
            try:
                # parse manuscript and version number from the title
                article_id, version = github_provider.detail_from_issue_title(
                    issue.title
                )
                if not article_id or not version:
                    self.logger.info(
                        (
                            "%s, could not parse the article_id and version"
                            " from the Github issue title '%s'"
                        )
                        % (self.name, issue.title)
                    )
                    continue

                # add a workflow to the starter queue
                self.start_post_workflow(article_id, version)

                # remove elife-bot as an assignee of the issue
                self.logger.info(
                    "%s, removing assignee %s from the Github issue"
                    % (self.name, self.settings.github_named_user)
                )
                github_provider.remove_github_issue_assignee(
                    issue, self.settings.github_named_user
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, exception raised processing issue '%s': %s"
                    % (self.name, issue.title, str(exception))
                )

        return self.ACTIVITY_SUCCESS

    def start_post_workflow(self, article_id, version):
        "start a workflow after a preprint is first published"
        # build message
        workflow_name = "IngestMeca"
        workflow_data = {
            "article_id": article_id,
            "version": version,
            "standalone": False,
        }
        message = {
            "workflow_name": workflow_name,
            "workflow_data": workflow_data,
        }
        self.logger.info(
            "%s, starting a %s workflow for article_id %s, version %s",
            self.name,
            workflow_name,
            article_id,
            version,
        )
        # connect to the queue
        queue_url = self.sqs_queue_url()
        # send workflow starter message
        self.sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
        )

    def sqs_connect(self):
        "connect to the queue service"
        if not self.sqs_client:
            self.sqs_client = self.settings.aws_conn(
                "sqs",
                {
                    "aws_access_key_id": self.settings.aws_access_key_id,
                    "aws_secret_access_key": self.settings.aws_secret_access_key,
                    "region_name": self.settings.sqs_region,
                },
            )

    def sqs_queue_url(self):
        "get the queues"
        self.sqs_connect()
        queue_url_response = self.sqs_client.get_queue_url(
            QueueName=self.settings.workflow_starter_queue
        )
        return queue_url_response.get("QueueUrl")
