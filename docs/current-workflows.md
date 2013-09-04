======
Current eLife Bot Workflows
======

SWF supports workflows that are composed of activities. 

## Current Workflows

### LensIndexPublish Workflow

Publish eLife Lens documents index file and other supporting files to CDN.


### AdminEmail workflow

Email administrators status messages.


### LensArticlePublish workflow

Publish an article to eLife Lens CDN.



### PublishArticle workflow

Push article metadata to Fluidinfo, in order to support eLife API.


### PublishPDF workflow

Publish article PDF workflow.


### S3Monitor workflow
Monitoring an S3 bucket for modifications.


## Current Activities

### AdminEmailHistory

Email administrators a workflow history status message.

### ArticleToFluidinfo

Publish article to Fluidinfo.

### ConverterXMLtoJS

PUT XML into the converter, then GET the JSON and JSONP, and then save those to the S3 CDN bucket.

### LensCDNInvalidation

Create an invalidation request for the eLife Lens documents in the Cloudfront CDN.

### LensDocumentsJS

Create the eLife Lens documents file in JSON and JSONP, and then save those to the S3 CDN bucket.

### LensXMLFilesList

Create the eLife Lens xml list file for cache warming, and then save those to the S3 CDN bucket.

### PingWorker

Ping a worker to check if running.

### S3Monitor

S3Monitor activity: poll S3 bucket and save object metadata into SimpleDB.

### UnzipArticlePDF

Download a S3 object from the elife-articles bucket (``bucket``), unzip if necessary, and save to the elife-cdn bucket (``cdn_bucket``).

### UnzipArticleXML

Download a S3 object from the elife-articles bucket (``bucket``), unzip if necessary, and save to the elife-cdn bucket (``cdn_bucket``).

### WorkflowConflictCheck

Check for open workflows to determine logical conflicts, when two workflow types should not run concurrently.