import json
import os
import importlib

import boto.swf

import workflow
import activity
from provider import utils

"""
Amazon SWF register workflow or activity utility
"""

def start(settings):

    # Simple connect
    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

    workflow_names = []
    workflow_names.append("CopyGlencoeStillImages")
    workflow_names.append("SilentCorrectionsIngest")
    workflow_names.append("SilentCorrectionsProcess")
    workflow_names.append("IngestArticleZip")
    workflow_names.append("InitialArticleZip")
    workflow_names.append("ProcessArticleZip")
    workflow_names.append("Ping")
    workflow_names.append("ApproveArticlePublication")
    workflow_names.append("LensArticlePublish")
    workflow_names.append("AdminEmail")
    workflow_names.append("PackagePOA")
    workflow_names.append("PublishPOA")
    workflow_names.append("DepositCrossref")
    workflow_names.append("DepositCrossrefPeerReview")
    workflow_names.append("PubmedArticleDeposit")
    workflow_names.append("PublicationEmail")
    workflow_names.append("FTPArticle")
    workflow_names.append("PubRouterDeposit")
    workflow_names.append("PMCDeposit")
    workflow_names.append("PostPerfectPublication")
    workflow_names.append("IngestDigest")
    workflow_names.append("IngestDecisionLetter")
    workflow_names.append("SoftwareHeritageDeposit")

    for workflow_name in workflow_names:
        # Import the workflow libraries
        class_name = "workflow_" + workflow_name
        module_name = "workflow." + class_name
        importlib.import_module(module_name)
        full_path = "workflow." + class_name + "." + class_name
        # Create the workflow object
        f = eval(full_path)
        logger = None
        workflow_object = f(settings, logger, conn)

        # Now register it
        response = workflow_object.register()

        print(('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)))

    activity_names = []
    activity_names.append("ReadyToPublish")
    activity_names.append("VersionReasonDecider"),
    activity_names.append("AcceptVersionReason"),
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
    activity_names.append("DepositCrossrefPeerReview")
    activity_names.append("PubmedArticleDeposit")
    activity_names.append("PublicationEmail")
    activity_names.append("FTPArticle")
    activity_names.append("PubRouterDeposit")
    activity_names.append("PMCDeposit")
    activity_names.append("ScheduleCrossref")
    activity_names.append("ScheduleCrossrefPeerReview")
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
    activity_names.append("DownstreamStart")
    activity_names.append("PackageSWH")

    for activity_name in activity_names:
        # Import the activity libraries
        class_name = "activity_" + activity_name
        module_name = "activity." + class_name
        importlib.import_module(module_name)
        full_path = "activity." + class_name + "." + class_name
        # Create the workflow object
        f = eval(full_path)
        logger = None
        activity_object = f(settings, logger, conn)

        # Now register it
        response = activity_object.register()

        print(('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)))

if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    start(SETTINGS)
