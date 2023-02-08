import json
import importlib
import os
import boto3
import workflow
import activity
from provider import utils

"""
Amazon SWF register workflow or activity utility
"""


def start(settings):

    # Connect to SWF to get client
    swf_client = boto3.client(
        "swf",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.swf_region,
    )

    workflow_names = []
    workflow_names.append("CopyGlencoeStillImages")
    workflow_names.append("SilentCorrectionsIngest")
    workflow_names.append("SilentCorrectionsProcess")
    workflow_names.append("IngestArticleZip")
    workflow_names.append("ProcessArticleZip")
    workflow_names.append("Ping")
    workflow_names.append("ApproveArticlePublication")
    workflow_names.append("LensArticlePublish")
    workflow_names.append("AdminEmail")
    workflow_names.append("PackagePOA")
    workflow_names.append("PublishPOA")
    workflow_names.append("DepositCrossref")
    workflow_names.append("DepositCrossrefPeerReview")
    workflow_names.append("DepositCrossrefPendingPublication")
    workflow_names.append("PubmedArticleDeposit")
    workflow_names.append("PublicationEmail")
    workflow_names.append("FTPArticle")
    workflow_names.append("PubRouterDeposit")
    workflow_names.append("PMCDeposit")
    workflow_names.append("PostPerfectPublication")
    workflow_names.append("IngestDigest")
    workflow_names.append("IngestDecisionLetter")
    workflow_names.append("DepositDOAJ")
    workflow_names.append("SoftwareHeritageDeposit")
    workflow_names.append("IngestAcceptedSubmission")

    for workflow_name in workflow_names:
        # Import the workflow libraries
        class_name = "workflow_" + workflow_name
        module_name = "workflow." + class_name
        module_object = importlib.import_module(module_name)
        workflow_class = getattr(module_object, class_name)
        # Create the workflow object
        logger = None
        workflow_object = workflow_class(settings, logger, client=swf_client)

        # Now register it
        response = workflow_object.register()

        print(("got response: \n%s" % json.dumps(response, sort_keys=True, indent=4)))

    activity_names = []
    activity_names.append("ReadyToPublish")
    activity_names.append("InvalidateCdn")
    activity_names.append("ConvertImagesToJPG")
    activity_names.append("SendDashboardProperties")
    activity_names.append("DepositIngestAssets")
    activity_names.append("CopyGlencoeStillImages")
    activity_names.append("VerifyImageServer")
    activity_names.append("GeneratePDFCovers")
    activity_names.append("VerifyGlencoe")
    activity_names.append("UpdateRepository")
    activity_names.append("VersionLookup")
    activity_names.append("VersionDateLookup")
    activity_names.append("VerifyPublishResponse")
    activity_names.append("PublishToLax")
    activity_names.append("VerifyLaxResponse")
    activity_names.append("IngestToLax")
    activity_names.append("PingWorker")
    activity_names.append("ExpandArticle")
    activity_names.append("ApplyVersionNumber")
    activity_names.append("ArchiveArticle")
    activity_names.append("DepositAssets")
    activity_names.append("AdminEmailHistory")
    activity_names.append("LensArticle")
    activity_names.append("PackagePOA")
    activity_names.append("PublishFinalPOA")
    activity_names.append("DepositCrossref")
    activity_names.append("DepositCrossrefMinimal")
    activity_names.append("DepositCrossrefPeerReview")
    activity_names.append("DepositCrossrefPendingPublication")
    activity_names.append("PubmedArticleDeposit")
    activity_names.append("PublicationEmail")
    activity_names.append("FTPArticle")
    activity_names.append("PubRouterDeposit")
    activity_names.append("PMCDeposit")
    activity_names.append("ScheduleCrossref")
    activity_names.append("ScheduleCrossrefMinimal")
    activity_names.append("ScheduleCrossrefPeerReview")
    activity_names.append("ScheduleCrossrefPendingPublication")
    activity_names.append("ScheduleDownstream")
    activity_names.append("ModifyArticleSubjects")
    activity_names.append("EmailDigest")
    activity_names.append("DepositDigestIngestAssets")
    activity_names.append("CopyDigestToOutbox")
    activity_names.append("IngestDigestToEndpoint")
    activity_names.append("PublishDigest")
    activity_names.append("ValidateDigestInput")
    activity_names.append("EmailVideoArticlePublished")
    activity_names.append("CreateDigestMediumPost")
    activity_names.append("PostDigestJATS")
    activity_names.append("ValidateDecisionLetterInput")
    activity_names.append("GenerateDecisionLetterJATS")
    activity_names.append("DecisionLetterReceipt")
    activity_names.append("DepositDecisionLetterIngestAssets")
    activity_names.append("PostDecisionLetterJATS")
    activity_names.append("DepositDOAJ")
    activity_names.append("DownstreamStart")
    activity_names.append("PackageSWH")
    activity_names.append("GenerateSWHMetadata")
    activity_names.append("GenerateSWHReadme")
    activity_names.append("PushSWHDeposit")
    activity_names.append("ExpandAcceptedSubmission")
    activity_names.append("RepairAcceptedSubmission")
    activity_names.append("ValidateAcceptedSubmission")
    activity_names.append("TransformAcceptedSubmission")
    activity_names.append("EmailAcceptedSubmissionOutput")
    activity_names.append("ValidateAcceptedSubmissionVideos")
    activity_names.append("RenameAcceptedSubmissionVideos")
    activity_names.append("DepositAcceptedSubmissionVideos")
    activity_names.append("AnnotateAcceptedSubmissionVideos")
    activity_names.append("AddCommentsToAcceptedSubmissionXml")
    activity_names.append("OutputAcceptedSubmission")
    activity_names.append("AcceptedSubmissionPeerReviews")

    for activity_name in activity_names:
        # Import the activity libraries
        class_name = "activity_" + activity_name
        module_name = "activity." + class_name
        module_object = importlib.import_module(module_name)
        activity_class = getattr(module_object, class_name)
        # Create the workflow object
        logger = None
        activity_object = activity_class(settings, logger, client=swf_client)

        # Now register it
        response = activity_object.register()

        # clean up temporary directory
        activity_object.clean_tmp_dir()
        os.rmdir(activity_object.get_tmp_dir())

        print(("got response: \n%s" % json.dumps(response, sort_keys=True, indent=4)))


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    start(SETTINGS)
