======
Adding a new workflow to the eLife Bot
======

## Overview

This page describes the recommended method to modify or add new workflows to the eLife bot.

In order to run all the tests and get the code functioning correctly, you will need sufficient access to eLife S3 buckets, SimpleDB domains, etc. As an alternative, you can create your own running environment and create enter your particulars into the ``settings.py`` file for your own AWS services.

A brief summary of the steps:

### Planning

If you don't already understand the fundamentals of SWF and how eLife bot runs, you may want to review the documentation in more depth. There are some already built components to incorporate into what you are planning to build.

### Branch the code in git

In using git-flow branching model procedure, your new feature will be encapsulated and easy to merge later.

### Develop the activity

You can write new activity code without running SWF workflows, and sometimes even without having Internet access. An activity is where the real work happens. You can hack it together and run it from the command-line using python __main__. Or, you can write lettuce tests for its unique functions and run the tests to validate its integrity. Basically, you can start with the most friction-less method you choose, as long as you end up with some automated tests by the end!

### Run a mock workflow on your local computer

By connecting to your own private SWF task list, you can run the ``decider.py``, ``worker.py`` and issue a workflow execution start using the ``dev`` workflow, entirely from your own computer. This is after you've adapted or added the workflow and starter classes to make it run. This should shake out many possible errors in integrating with the SWF service.

### Add or modify a scheduled starter using cron

Add or modify the cron code to automatically start your workflow when it should. 

### Pull request in git

When you are confident your new features are ready to review, submit a pull request. Another developer _should_ review your code, run lettuce tests and mock workflows using SWF. Cron components, at this time, generally require deploying to a running instance in order to fully test them in that situation.

### Deploy

Merge to master branch and deploy ASAP to the running instance. See ``installation.md`` for more on deployments.


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

- Events that trigger a workflow to start are when a new pdf.zip file appears on S3, when an existing pdf.zip file is modified, or we may want to start it manually, perhaps running the activity on a single file, or all files
- When it runs automatically we want it to run as soon after the updated file appears as possible
- There are no additional steps at this time, but in future we may want to save the PDF to more than one location or service after it's unzipped

Knowing a little about the existing elife-bot code, we can assemble a rough plan:

Q. How do we determine if a new or updated article ``pdf.zip`` file appears?  
A. The SimpleDB provider functions can tell us (as a result of the continually run S3Monitor)  

Q. How do we schedule it to run when a new file appears?  
A. We can add a cron starter to the list of scheduled tasks in ``cron.py``  

Q. Is there an existing workflow the activity can be added to?   
A. Perhaps. It depends on the business logic and how we decide to build the workflows. In this case we say no, because no workflow is specific to pdf.zip files.  

Q. Is there an existing activity that can be adapted?  
A. Maybe, but in this case we say no. There is an activity that unzips ``xml.zip`` files and saves them to S3, but for flexibility and to simplify our getting going, we can duplicate that activity and make it specific to processing ``pdf.zip`` files.  

Q. Do we need to supply additional settings or credentials for the activities to work?  
A. In this case no, because it uses the same input and output S3 buckets that are already specified in our ``settings.py`` file. We will hardcode a ``/pdf/`` subdirectory name into the activity, so settings do not need modification.  

In summary, our rough plan is:

- Use existing settings parameters (Amazon S3 buckets)
- Use existing data providers
- Create a new activity, named ``activity_UnzipArticlePDF``
- Create a new workflow, named ``workflow_PublishPDF``
- Create a new starter, named ``starter_PublishPDF``
- Create a new cron starter, named ``cron_NewS3PDF``
- Add ``cron_NewS3PDF`` to the ``cron.py`` when we're done, to schedule it

``workflow_PublishPDF`` will have only one real activity, but in future we can add additional activities, such as uploading it to an additional endpoint.

``cron_NewS3PDF`` will at first only start one workflow per ``pdf.zip`` file, but in future we can add additional workflows it should start per ``pdf.zip`` file

In making the rough plan, it is probably easier to start top down: from where the data will come from (settings, data providers, S3), to a scheduled or manual trigger for starter(s), to the workflow(s), to the activity(ies) that need to run.

In building the items themselves, a good way to implement it is bottom up. Start with the activity itself, which can even be hacked at outside of the workflow at first. Integrate it into a new activity task, and ideally create automated tests for it.

You should be able to test almost everything via ``lettuce``, except for the ``do_activity()`` function, which is what a live workflow would run (unless it is safe to run, but tests are ideally do not make permanent changes to the system).


## Step 2: Create a git branch

Branch the elife-bot code with a descriptive feature name.

## Step 3: Develop the activity

You may have some existing code or you are starting from scratch. Described below is one recommended method to incorporate a new activity into eLife bot.

### Create a new activity class

Go into the __/activity__ folder, select an existing activity, save as a new file as you determined in the Step 1: Planning. File and class names are in the format ``activity_[ActivityType].py``. The activityType is the name you will register with SWF, and allows the ``worker.py`` to autoload the class by name.

Rename the class in in the python code. In the ``__init__`` method, Customise the ``self.name``, ``self.description`` and comments. The classe's default timeout values may be sufficient (``self.default_task_schedule_to_close_timeout`` etc.) but they can be overridden later in the workflow definition if you get them wrong at this stage.

### Modify the imports

Check which python libraries it imports. Sometimes it may include a provider or two (``provider.swfmeta`` or ``provider.simpledb``), or ``boto.ses`` for email. You may not need these, or you may need to import a new code library for your activity.

### Delete old code

Since you started with an existing activity class as a template, you'll want to delete much of the code from your new class. In ``do_activity()``, delete everything after the ``self.logger`` instantiation down, until the ``return True``. Then, delete everything below that. The file will be virtually empty, but it's safer to tear everything out first and then add what you need back in.

### Coding

To be expanded

- Can run as __main__
- Lettuce tests
- Note on reusable code

### Register with SWF

Add the ActivityType name to the ``register.py`` file, by appending the name to the ``activity_names`` list (you'll see a list in the code). Run it on the environment(s) you intend will schedule the activity. ``register.py`` will load your activity class, get the name, description, and timeout values and register it with SWF. It will also register all the activities listed in the file, but if they already exist, no modifications will be made.

_dev_ environment:

```
python register.py
```

_live_ environment:

```
python register.py -e live
```


## Step 4: Assemble the workflow components and test locally

- New workflow definition (Create a new workflow type) + starter, or
- Edit an existing workflow definition
- Register with SWF (if applicable)
- How to use a different task list

## Step 5: Add scheduled cron starter (if applicable)



## Step 6: Pull request and review

- Ready to deploy, but an option for someone else to also test your code locally, as described in Step 4, and get the green light
- You may want to note the addition of any new ``settings.py`` credentials required to run a test on the new branch
- Merge with master


## Step 7: Deploy and test




## Needs to cover:

To do:

- how to build a new workflow
- how that workflow gets started
- how to add a test for the new workflow
- finally how to deploy the new workflow	
