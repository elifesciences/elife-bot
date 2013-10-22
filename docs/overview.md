=======
elife-bot Overview
=========

eLife Bot is a set of tools built on top of Amazon's [Simple Work Flow][swf] (SWF) to manage post-publication workflow. After we publish an article within eLife we want a number of processes to happen. eLife Bot mocks an event driven architecture by monitoring an S3 bucket hourly for the arrival of new files. History is stored in an [Amazon Simple DB][sdb]. When a new or modified file is identified a workflow is trigged in [SWF][swf]. Our workflows have been configured to write files to S3 bucket objects and to save data into the SimpleDB. 

[swf]: http://aws.amazon.com/swf/
[sdb]: http://aws.amazon.com/simpledb/

A more detailed description of how eLife bot works is documented in `components.md`, including a description of a workflow lifecycle example and how it executes scheduled tasks using cron jobs.

## Installation and tests

eLife bot is currently configured and deployed manually via a custom Ec2 instance. This is partially described in `installation.md`. Tests are provided in `lettuce`. 


## Existing Workflows

Existing workflows are documented in `current-workflows.md`.


## Extending eLife bot with a new workflow

In principle this system can be extended horizontally. Adding new activities and workflows should be easy. For more details on how to develop eLife bot, read ``configuring-a-new-worker.md``.

## Amazon Simple Workflow Service (SWF)

Background information and tips are found in ``notes-on-swf.md``.

## SimpleDB

Detailed information about SimpleDB, how eLife bot uses it, and the particular object schema and fields, refer to ``simple-db.md``.

## Issues and Backlog

Issues and backlog items are stored in Github on the [project issues page][pip].

Major milestones that we would like to see are:

- setting up deployment via chef
- making extending the workflow super easy
- adding a visual reporting strucutre
- adding a way to poll external endpoints for ALM data (potentially)

[pip]: https://github.com/elifesciences/elife-bot/issues?labels=2+-+Working&milestone=2&state=open



## Contributing to the project

If you have a contribution you wouldl like us to consider, please send a pull request. 


## Other eLife Resources

This is part of the eLife suite of tools. You can find more resources at [dev.elifesciences.org](dev.elifesciences.org).


## About eLife

eLife is an open access publisher in the life sciences. 