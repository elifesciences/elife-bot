=======
elife-bot Components
=========

## Component diagram

In an effort to explain the components of the elife-bot, a diagram provided as part of the [AWS Flow Framework for Ruby][awsflow] documentation located at Amazon is adapted to illustrate the elife-bot:

[awsflow]: http://docs.aws.amazon.com/amazonswf/latest/awsrbflowguide/awsflow-basics-application-structure.html

![eLife bot diagram](images/elife-bot-diagram.png)

In short,

- ``worker.py`` command-line utility polls SWF for activity tasks every 60 seconds, and instantiates an activity class when it receives a task
- ``decider.py`` command-line utility polls SWF for decision tasks every 60 seconds, and instantiates an workflow class when it receives a task
- starters can start one or more workflows
- ``cron.py`` is run every 5 minutes and will load one or more starters when required
- additionally, a human operator can load a starter as required

## A workflow lifecycle example

To do.

![eLife bot cron diagram](images/elife-bot-cron.png)

## Performance notes

Example running

- on a t1.micro EC2 instance
- 3 decider.py processes in dev environment, 3 in live environment
- 5 worker.py processes in dev environment, 5 in live environment

General performance notes:

- Known to run for weeks uninterrupted between new code deployments
- RAM Mem: 604348k total, 557244k used, after real work performed
- S3Monitor, using a single worker, polls for modifications on 1,114 S3 objects in 2 min 44 sec
- Full conversion of 237 articles into eLife lens completes in 14 minutes
- Unzipping 230 PDF files and saving to S3, approx. 1.4 GB of data, takes 7 minutes
- Publishing 3 articles to Fluidinfo API takes 12 seconds



