import json
from argparse import ArgumentParser
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params
from provider import utils


class starter_ScheduleCrossrefPreprint(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_ScheduleCrossrefPreprint, self).__init__(
            settings, logger, "ScheduleCrossrefPreprint"
        )

    def get_workflow_params(
        self,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
    ):
        if article_id is None:
            raise NullRequiredDataException("Did not get an article id. Required.")

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (self.name, article_id)
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"

        info = {
            "run": run,
            "article_id": article_id,
            "version": version,
            "standalone": standalone,
        }
        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(
        self,
        settings,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
    ):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(
            article_id,
            version,
            run,
            standalone,
        )

    def start_workflow(
        self,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
    ):
        workflow_params = self.get_workflow_params(article_id, version, run, standalone)

        self.start_workflow_execution(workflow_params)


def main():

    # example on how to run:
    # From elife-bot folder run
    # python starter/starter_ScheduleCrossrefPreprint.py --env=dev --article-id=15224 --version=1

    parser = ArgumentParser()
    parser.add_argument(
        "-e",
        "--env",
        action="store",
        type=str,
        dest="env",
        help="set the environment to run, e.g. dev, live, prod, end2end",
    )
    parser.add_argument(
        "-a",
        "--article-id",
        action="store",
        type=str,
        dest="article_id",
        help="specify the article id to process",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store",
        type=str,
        dest="version",
        help="article version",
    )
    parser.set_defaults(env="dev", article_id=None, version=None)

    args = parser.parse_args()
    ENV = None
    if args.env:
        ENV = args.env
    article_id = None
    version = None
    if args.article_id:
        article_id = args.article_id
    if args.version:
        version = args.version

    settings = utils.get_settings(ENV)

    starter_object = starter_ScheduleCrossrefPreprint()

    starter_object.start(
        settings=settings,
        article_id=article_id,
        version=version,
        standalone=True,
    )


if __name__ == "__main__":
    main()
