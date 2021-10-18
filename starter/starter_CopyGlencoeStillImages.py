import json
from argparse import ArgumentParser
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params

"""
Amazon SWF CopyGlencoeStillImages starter, for copying Glencoe still images to IIIF bucket.
"""


class starter_CopyGlencoeStillImages(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_CopyGlencoeStillImages, self).__init__(
            settings, logger, "CopyGlencoeStillImages"
        )

    def get_workflow_params(
        self,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
        standalone_is_poa=False,
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
            "standalone_is_poa": standalone_is_poa,
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
        standalone_is_poa=False,
    ):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(
            article_id,
            version,
            run,
            standalone,
            standalone_is_poa,
        )

    def start_workflow(
        self,
        article_id=None,
        version=None,
        run=None,
        standalone=False,
        standalone_is_poa=False,
    ):

        workflow_params = self.get_workflow_params(
            article_id, version, run, standalone, standalone_is_poa
        )

        self.start_workflow_execution(workflow_params)


def main():

    # example on how to run:
    # From elife-bot folder run
    # python starter/starter_CopyGlencoeStillImages.py --env=dev --article-id=15224 --no-poa

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
        "-p",
        "--poa",
        action="store_true",
        dest="poa",
        help="Article is POA. If omitted it defaults to False.",
    )
    parser.add_argument(
        "-np",
        "--no-poa",
        action="store_false",
        dest="poa",
        help="Article is NOT POA. If omitted it defaults to False.",
    )
    parser.set_defaults(env="dev", article_id=None, poa=False)

    args = parser.parse_args()
    ENV = None
    if args.env:
        ENV = args.env
    article_id = None
    is_poa = False
    if args.article_id:
        article_id = args.article_id
    if args.poa:
        is_poa = args.poa

    import settings as settingsLib

    settings = settingsLib.get_settings(ENV)

    starter_object = starter_CopyGlencoeStillImages()

    starter_object.start(
        settings=settings,
        article_id=article_id,
        standalone=True,
        standalone_is_poa=is_poa,
    )


if __name__ == "__main__":
    main()
