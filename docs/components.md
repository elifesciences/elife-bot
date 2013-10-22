=======
elife-bot Components
=========

## Component diagram

In an effort to explain the components of the elife-bot, a diagram provided as part of the [AWS Flow Framework for Ruby][awsflow] documentation located at Amazon is adapted to illustrate the elife-bot:

[awsflow]: http://docs.aws.amazon.com/amazonswf/latest/awsrbflowguide/awsflow-basics-application-structure.html

![eLife bot diagram](images/elife-bot-diagram.png)

In short,

- ``worker.py`` command-line utility polls SWF for activity tasks every 60 seconds, and instantiates an ``activity`` class when it receives a task
- ``decider.py`` command-line utility polls SWF for decision tasks every 60 seconds, and instantiates a ``workflow`` class when it receives a task
- starters can start one or more workflows
- ``cron.py`` is run every 5 minutes and will load one or more starters when required
- additionally, a human operator can load a starter as required

To keep things tidy, all the ``activity`` classes are in the activity folder of the codebase, and all ``workflow`` classes are stored in the workflow folder.

The code components as part of eLife bot are primarily influenced by Amazon SWF and how it processes workflows. Please read the ``notes-on-swf.md`` page for more information about how workflows are processed by SWF.

In addition to the components in the diagram above, code found in the ``providers`` folder is shared by many components. This includes getting data from SimpleDB, looking up SWF workflow history, and using the local filesystem, including the ability to unzip files.

- ``filesystem.py`` can create a temporary directory, download files by URL, save files to disk, unzip zip files, read temporary directory contents, etc.
- ``simpleDB.py`` connects to SimpleDB, specifies a domain or creates a domain, and has eLife specific functions to access S3 monitoring data, email queue data
- ``swfmeta.py`` connects to Amazon SWF and can get lists of open workflows, closed workflows (by name, id or closed status), and also get the time a completed workflow was last started

All connections made to Amazon AWS services are done using the ``boto`` library. The actions performed include:

- Reading and writing files to S3
- Reading and writing data to SimpleDB
- Interfacing with Amazon SWF (using ``boto.swf``, ``boto.swf.layer1`` and ``boto.swf.layer1_decisions``), which essentially communicates with SWF via the RESTful API provided by Amazon

## Components in detail

Each of the important components of the system deserve an expanded description, included in the following.

### Filesystem provider

At first only one or two activities in the system did read and write of data to the file system. As the system expanded, the file system functions were spun off into a separate file for all to use.

Each activity of each workflow execution gets its own temporary directory, inside the ``/tmp`` folder. The subfolder name will be unique and separate from any other activity.

Writing data to disk: Primarily, the filesystem provider will take an S3 bucket URL to a file and download it, or you can use it to save data stored in memory to disk.

If you download a ``.zip`` file, the filesystem provider will automatically unzip it. It will also know what files were inside the zip file so you can use them later.

__Tests:__ In ``tests/features/006_provider_filesystem.feature`` there is (at the time of writing) one test that specifically unzips a file using the filesystem provider. But, other tests, such as ``tests/features/044_activity_UnzipArticlePDF.feature``, and many other tests depend on the filesystem provider to complete the testing steps. If you break the filesystem provider it should be evident with unsuccessful tests.

### SimpleDB provider

Querying SimpleDB data is much faster than relying on data in S3 storage. For that reason, eLife bot stores the result of polling S3 for file modifications, and keeps track of things like the email queue, in SimpleDB. It understands some simple SQL-like queries to quickly get the data you want fast.

The SimpleDB provider connects to SimpleDB. It also has some presets for where it should find particular data. If the domain (like a database table) does not exist, it creates it and connects to it.

There are some simple functions to get an item, or put item attributes.

Specific to how eLife uses SimpleDB, there are functions to return specific S3 bucket results, and also to count unsent emails in the email queue.

__Tests:__ In ``tests/features/005_provider_simpleDB.feature`` there are some example queries for running on S3 bucket logs data. The tests also load JSON data from the ``tests/test_data`` folder which simulates the results you would expect when querying SimpleDB using ``boto``. This saves having to write tests that connect live to AWS.

### SWFMeta provider

Amazon SWF keeps a maximum 90 day history of all workflow executions. The SWFMeta provider connects directly to SWF, via ``boto``, and issues requests on the open or closed workflow executions. The intention is this provider will provide any metadata about SWF, hence the name, SWFMeta.

It will continue to page for results when a nextPageToken is returned by Amazon until the full history of executions is received. But, when looking up the last run time of a particular workflow, it uses speedy adaptable time period magic.

Data comes straight from the "horses mouth", i.e. it is the official data returned directly by SWF service.

It is currently used in two ways,

- The cron (scheduled) jobs use it to keep track of when workflows were run and whether it is time to start a new workflow
- The completed workflow executions over a 4 hour time period is requested and a text summary of the status is emailed to administrators

__Tests:__ In ``tests/features/007_provider_swfmeta.feature`` there are some simple tests that load JSON data from the ``tests/test_data`` folder which simulates the results you would expect when querying SimpleDB using ``boto``.

### workflow class

A workflow represents the business logic that continues a workflow to completion (or failure).

The ``decider.py`` command-line script receives JSON as part of a decision task from SWF. It instantiates a workflow object and gives it the JSON. The job of the worklfow object is to figure out what to do next.

The plumbing in this procedure is in the base ``workflow/workflow.py`` class file. It looks at the JSON and figures out what activities are completed, what activities are not yet completed, and schedules the next activities to be done. It also may find all the activities were completed and subsequently it will close the workflow.

__Tests:__ The ``tests/features/010_decider.feature`` tests load an example JSON file from the ``tests/test_data`` folder for a decision task and instantiates a workflow object. The tests ``tests/features/030_workflow_types.feature`` instantiate some workflow classes.

### activity class

An activity represents real work to do as part of a workflow execution. It also receives JSON data provided by SWF.

The ``worker.py`` command-line script receives JSON as part of an activity task from SWF. It instantiates an activity object and gives it the JSON. The job of the activity object is to ``do_activity()`` using the data it is provided.

__Tests:__  The ``tests/features/020_worker.feature`` loads an example JSON file from the ``tests/test_data`` folder for emulated activity task JSON. In ``tests/features/041_activity.feature`` the tests load data in the form of JSON from the ``tests/test_data`` folder and runs it. There are also a number of tests written for specific activity classes in the 040 range of file names in the test folder.


## A workflow lifecycle example

When eLife bot runs continuously and autonomously, it runs on an hourly schedule. In the first half of each hour it checks for new or updated files, and logs those changes to a DB. In the second half of each hour it will perform actions on those files.

A simple diagram follows to help describe the automated workflows:

![eLife bot cron diagram](images/elife-bot-cron.png)

Overview:

- An instance cron job executes ``cron.py`` every 5 minutes.
- If it is the top half of the hour (i.e. if the time is 1:00 to 1:29, 2:00 to 2:29, etc.), it will execute ``S3Monitor`` if the last time ``S3Monitor`` was started is more than 31 minutes ago.
- ``S3Monitor`` will poll the S3 bucket for objects and log any object modifications in SimpleDB. The green arrow, in the sample diagram, indicates if ``S3Monitor`` runs at 2:00, it will be aware of files updated since 1:00.
- If it is the bottom half of the hour (i.e. if the time is 1:30 to 1:59, 2:30 to 2:59, etc.), it will execute ``cron_NewS3XML`` if the last time ``cron_NewS3XML`` was started is more than 31 minutes ago (as well as other executions)
- ``cron_NewS3XML``, for example, decides whether it should start any workflows, based on whether it discovers new files were added or changed to the S3 bucket since a lastUpdated date. It calculates the lastUpdated date as the previous time itself was started, minus 30 minutes. The green arrow, in the sample diagram, shows how it calculates it should look at files updated since 1:00.
- Because when ``S3Monitor`` ran at 2:00 it will only have logged objects updated until 2:00, the result will be ``cron_NewS3XML`` will operate on files updated between 1:00 an 2:00

Caveats: A keen reader may wonder what happens if an S3 object is updated while the S3Monitor is running. In short, it still works: objects updated since the S3Monitor has already passed them will get logged in the next hour; objects updated before the S3Monitor reaches them will get logged that hour, due to the atomicity of S3Monitor operations.

Continuing the workflow lifecycle:

- Say that ``cron_NewS3XML`` finds 3 S3 objects were new or updated since 1:00 that contain new article XML
- ``cron_NewS3XML`` will execute multiple starters, as many as are listed in the code to start when new XML is found. Some starters will be given the lastUpdated date, some may not require it.
- Each starter, in turn, will start multiple SWF workflow executions, or a single workflow, depending on what the starter does. For example, 3 new XML objects will result in starting 3 PublishArticle workflows.
- Once a workflow execution is started, the ``decider.py`` and ``worker.py`` processes that are listening on the job queue will process the business logic or activity steps, respectively.
- Each workflow execution will progress as programmed until the workflow execution is COMPLETED, FAILED, or TIMED_OUT (the common status values expected in automated jobs)

Note on time clocks: In comparing the time on an EC2 micro instance and the time used in the SWF queue, the times can differ by more than 60 seconds. Preliminary results from searching the AWS forums indicate there is no approved method to synchronize clocks with the clock used by SWF. When planning cron (scheduled) jobs and calculating time, this greater than 60 second disparity may matter.

## Performance notes

Example running

- on a t1.micro EC2 instance
- 3 decider.py processes in dev environment, 3 in live environment
- 5 worker.py processes in dev environment, 5 in live environment

General performance notes:

- Known to run for weeks uninterrupted between new code deployments
- RAM Mem: 604348k total, 557244k used, after real work performed
- S3Monitor, using a single worker, polls for modifications on 1,700 S3 objects in 4 to 8 minutes
- Unzipping 230 PDF files and saving to S3, approx. 1.4 GB of data, takes 7 minutes
- Publishing 6 articles worth of content (XML, PDF, SVG, eLife lens page, and Fluidinfo API) takes 48 seconds
- Publishing 3 articles to Fluidinfo API takes 12 seconds



