=======
Notes on SWF
=========

## Overview

Amazon [Simple Workflow][swf] (SWF) service provides a structured approach to execute business logic. This page highlights the use of SWF specifically in an eLife bot context.

[swf]: http://aws.amazon.com/swf/

## Further reading

* [Amazon Simple Workflow Service Developer Guide -  Basic Concepts](http://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dg-basic.html) with pictures!
* [Using Python to access Amazon Simple Workflow (SWF)](http://open.pbs.org/blog/2012/using-python-access-amazon-simple-workflow-swf/)
* [SWF in boto documentation](http://boto.readthedocs.org/en/latest/ref/swf.html)
* Also, **boto/swf/layer1_decisions.py** file is not documented on the web, you can review the code itself

## Why use SWF?

- It is used by Amazon to run their own operations.
- It is provided as a service with no additional management required
- The architecture is ready to scale horizontally
- Specifying business logic is flexible

## General concepts and tips

### Domain

An SWF domain is like a top level container. Inside, it holds a list of workflow types, activity types, and a workflow execution history. You specify a particular domain when you connect to SWF. A domain is created only  once, either in the AWS console or programmatically.

In eLife bot there are currently two domains: ``Publish`` and ``Publish.dev``.

### Workflow Types

A workflow is business logic alone. During expected workflow operation, it schedules activity tasks and signals the completion of a workflow execution. If something unexpected happens in a workflow, the worklfow timeout values allow SWF to determine if a workflow failed due abandonment or non-completion.

A decider makes decisions about what activities to schedule, or when it is time to close a workflow execution. How a decider is implemented in code is entirely up to the developer.

In eLife bot, all decisions are ultimately made by ``decider.py``, though it loads particular workflow classes for the logic of each workflow type.

If a decider does not process SWF decision tasks, a workflow execution does not proceed. Therefore, a decider must always be running and polling for decision tasks to continuously run in SWF.

Each Workflow Type has a Name and Version. It also has default timeout values for different actions. __To use a Workflow Type, you must register it with SWF__. If SWF is not aware of a Workflow Type, it will not start workflow executions of that type.

### Activity Types

An activity is where real processing is done.

A worker, after receiving an activity task, will do something. Then, it can signal back to SWF whether the action was completed or failed. If the activity timed out as part of a workflow execution, SWF will often attempt the activity again, so long as the workflow's timeout has not yet been reached.

If no worker is polling for activity tasks, a workflow will likely timeout and not reach completion. Certain, no work will ever get done in the workflow execution.

In eLife bot, all activities are ultimately processed by ``worker.py``, though it loads particular activity classes and calls the ``do_activity()`` function of the class to execute the activity.

Each Activity Type has a Name and Version. It also has default timeout values for different actions. __To use a Activity Type, you must register it with SWF__. If SWF is not aware of a Activity Type, a decider will not be able to schedule activities of that type.

### Task list

A task list is where deciders and workers look for new tasks. When polling SWF, you specify a domain and task list. You also specify the domain and task list when starting a workflow execution.

One method of using task lists will be covered in ``configuring-a-new-worker.md`` during development. While the "live" decider and worker processes are polling one task list, you can run deciders and workers on a different system that are polling a different task list. Otherwise, you will end up with cross-talk between the two systems and a decider + worker battle to see which can poll for tasks first.

### Workflow executions

By comparison with a Workflow Type, a workflow execution refers to a particular workflow execution that is run. Each workflow execution will have a:

- runID
- start date
- closed date
- closed status
- list of events, such as decision tasks and activities scheduled
- list of activities with their start and completion dates
- and other metrics

This data is stored in the Amazon SWF domain for up to 90 days, and can be accessed as part of the workflow execution history.

In order to start a workflow execution, you issue a start workflow execution request.

### Starters

Very little is required to start a workflow execution. At the very least, you must specify the Workflow Type, Version and typically some input data. Specifying or overriding the default workflow timeout values is also an option.

Regardless of starter simplicity, eLife bot expresses starters in class definitions. These provide a uniform starter function, allow a human operator to issue command-line workflow starts with minimal input, and allow scheduled workflows to be started by the cron. 

### Unique IDs

Within an SWF domain, each _running_ workflow execution must have a unique workflow_id. Closed workflow executions with the id are ok.

Similarly, within a workflow execution, each activity must have a unique activity_id.

### Other notes

- There is no built-in cron or scheduled job facility provided by SWF. You need to bring your own.
- There is no standarized way to synchronize your machine clock with the clock that is running at SWF

## How eLife bot uses SWF

eLife bot uses ``boto`` functions to connect to SWF, which in turn makes use of the RESTful API for SWF. It __does not__ use any "flow" frameworks provided by Amazon.

### Deciders and workers are independent

Any worker, listening on the same SWF task list, may process any activity. The same is true for any decider that is making decision tasks. Consider a workflow with two activity steps: in a workflow execution,

- The machine executing step 1 may not be the same machine that executes step 2
- Similarly, a decider that decides to schedule step 1 may not be the same decider that schedules step 2
- Each activity gets its own temporary directory, so activities executed on the __same__ machine will not read files saved by some other activity

### Shared data and data persistence

Any useful or important data must be stored outside of an eLife bot instance. Save data to S3 or SimpleDB so it can be used by the next worker or some time in the future. Each worker running in a particular environment (``dev`` or ``live``) will share the same S3 buckets and SimpleDB domains with all other workers in that environment.

The SWF execution history that is automatically created and stored by Amazon for up to 90 days also provides some semi-permanent data, though of course this is deleted automatically after 90 days.

### Input data to a workflow

Currently, when starting a workflow execution, you must provide the custom data all activities as part of that workflow will require to complete the activities. For processing article files, this is typically:

- 5 digits of a DOI (e.g 00776)
- The URL of a zip file on S3 to process

### Making decisions

- When eLife bot ``decider.py`` polls for decision tasks (using ``boto.swf.layer1.poll_for_activity_task``), it will download a full workflow execution history if a ``next_page_token`` is provided by SWF. The default is to only return a maximum of 100 event history items returned in each poll request.

### Hacks

eLife bot uses a small hack issuing ``Ping`` workflows with a particular workflow ID to keep track of when cron workflows are run. Therefore, it makes no use of SWF's signals or tags.


