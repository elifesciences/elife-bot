import json
import uuid
from argparse import ArgumentParser
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params
from provider import utils


class starter_FinishPreprintPublication(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_FinishPreprintPublication, self).__init__(
            settings, logger, "FinishPreprintPublication"
        )
        self.execution_start_to_close_timeout = str(60 * 60)

    def get_workflow_params(
        self,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
        run_type=None,
        pdf_url=None,
    ):
        if article_id is None:
            raise NullRequiredDataException("Did not get an article id. Required.")
        if version is None:
            raise NullRequiredDataException("Did not get an version. Required.")

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (self.name, article_id)
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params[
            "execution_start_to_close_timeout"
        ] = self.execution_start_to_close_timeout

        info = {
            "run": run,
            "article_id": article_id,
            "version": version,
            "standalone": standalone,
            "run_type": run_type,
            "pdf_url": pdf_url,
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
        run_type=None,
        pdf_url=None,
    ):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(
            article_id,
            version,
            run,
            standalone,
            run_type,
            pdf_url,
        )

    def start_workflow(
        self,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
        run_type=None,
        pdf_url=None,
    ):
        if run is None:
            run = str(uuid.uuid4())

        workflow_params = self.get_workflow_params(
            article_id, version, run, standalone, run_type, pdf_url
        )

        self.start_workflow_execution(workflow_params)


def main():
    # example on how to run:
    # From elife-bot folder run
    # python starter/starter_PostPreprintPublication.py --env=dev --article-id=15224 --version=1

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

    starter_object = starter_FinishPreprintPublication()

    starter_object.start(
        settings=settings,
        article_id=article_id,
        version=version,
        standalone=False,
    )


if __name__ == "__main__":
    main()
