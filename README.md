=======
elife-bot Overview
=========

eLife Bot is a set of tools built on top of Amazon's [Simple Work Flow][swf] (SWF) to manage post-publication workflow. After we publish an article within eLife we want a number of processes to happen. eLife Bot mocks an event driven architecture by monitoring an S3 bucket hourly for the arrival of new files. History is stored in an AWS Simple DataBase. When a new or modified file is identified a workflow is trigged in [SWF][swf]. Our workflows have been configured to write logging information back into the Simple DB. 


## Installation and tests

eLife bot is currently configured and deployed manually via a custom Ec2 instance. This is partially described in `installation.md`. Tests are provided in `lettuce`.

We have added unit tests for the eLife bot activities using Python unittest library. Running on the command line:
cd to elife-bot and execute:
python -m pytest --junitxml=build/junit.xml tests/


## Existing Workflows

Existing workflows are documentd in `current-workflows.md`.


## Extending eLife bot with a new workflow

In principle this system can be extended horizontally. Adding new workers and workflows should be easy. 


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

This is part of the eLife suite of tools. You can find more resources at [elifesciences.org](elifesciences.org).


## About eLife

eLife is an open access publisher in the life sciences. We are supported by [The Wellcome Trust](http://www.wellcome.ac.uk/), [The Howard Hughes Medical Institute](http://www.hhmi.org/) and [The Max Planck Society](http://www.mpg.de/en). We publish at [elifescience.org](http://elifesciences.org/).

# Copyright & Licence

Copyright 2016 eLife Sciences. Licensed under the [MIT license](LICENSE).
