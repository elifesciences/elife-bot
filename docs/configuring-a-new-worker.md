======
Adding a new workflow to the eLife Bot
======

## Step 1: Planning a new workflow

Ask yourself the following:

- what activity will it do, or multiple activities?
- what event causes it to start, or are there multiple ways for it to start?
- when should it run?
- does the activity have multiple steps or dependencies?
- etc.

As an example, let's try adding something new. Expressed as a use case,

	Given we have a zipped PDF file for an article in an S3 bucket, we want to unzip it and save it to Amazon S3.

Seems simple. This generally describes the first question - what activity does it perform. In answering more of our questions:

- Events that trigger a workflow start are when a new pdf.zip file appears on S3, when an existing pdf.zip file is modified, or we may want to start it manually, perhaps running the activity on a single file, or all files
- When it runs automatically we want it to run as soon after the updated file appears as possible
- There are no additional steps at this time, but in future we may want to save the PDF to more than one location or service after it's unzipped

Knowing a little about the existing elife-bot code, we can assemble a rough plan:

Q. How do we determine if a new or updated article ``pdf.zip`` file appears? A. The SimpleDB provider functions can tell us (as a result of the continually run S3Monitor)
Q. How do we schedule it to run when a new file appears? A. We can add a cron starter to the list of scheduled tasks in ``cron.py``
Q. Is there an existing workflow the activity can be added to? A. Perhaps. It depends on the business logic and how we decide to build the workflows. In this case we say no, because no workflow is specific to pdf.zip files.
Q. Is there an existing activity that can be adapted? A. Maybe, but in this case we say no. There is an activity that unzips ``xml.zip`` files and saves them to S3, but for flexibility and to simplify our getting going, we can duplicate that activity and make it specific to processing ``pdf.zip`` files.
Q. Do we need to supply additional settings or credentials for the activities to work? A. In this case no, because it uses the same input and output S3 buckets that are already specified in our ``settings.py`` file. We will hardcode a ``/pdf/`` subdirectory name into the activity, so settings do not need modification.

In summary, our rough plan is:

- Use existing settings parameters (Amazon S3 buckets)
- Use existing data providers
- Create a new activity, named ``activity_UnzipArticlePDF``
- Create a new workflow, named ``workflow_PublishPDF``
- Create a new cron starter, named ``cron_NewS3PDF``
- Add ``cron_NewS3PDF`` to the ``cron.py`` when we're done, to schedule it

``workflow_PublishPDF`` will have only one real activity, but in future we can add additional activities, such as uploading it to an additional endpoint.

``cron_NewS3PDF`` will at first only start one workflow per ``pdf.zip`` file, but in future we can add additional workflows it should start per ``pdf.zip`` file

In making the rough plan, it is probably easier to start top down: from where the data will come from (settings, data providers, S3), to a scheduled or manual trigger for starter(s), to the workflow(s), to the activity(ies) that need to run.

In building the items themselves, a good way to implement it is bottom up. Start with the activity itself, which can even be hacked at outside of the workflow at first. Integrate it into a new activity task, and ideally create automated tests for it.

You should be able to test almost everything via ``lettuce``, except for the ``do_activity()`` function, which is what a live workflow would run (unless it is safe to run, but tests are ideally do not make permanent changes to the system).



## Needs to cover:

To do:

- how to build a new workflow
- how that workflow gets started
- how to add a test for the new workflow
- finally how to deploy the new workflow	