=======
elife-bot Overview
=========

eLife Bot is a set of tools built on top of Amazon's [Simple Work Flow][swf] (SWF) to manage publication workflow. The workflows, activities, and libraries change often to support eLife's evolving requirements.

When we publish an article within eLife we want a number of processes to happen. eLife Bot incorporates an event driven architecture from S3 bucket notifications when new files arrive. History is stored in an AWS Simple DataBase, as well as in S3 buckets. When a new or modified file is identified a workflow is trigged in [SWF][swf].

[swf]: https://aws.amazon.com/swf/


## Digest silent workflow

Digest zip files copied to the digest input bucket (a bucket with a name matching `*-elife-bot-digests-input`) will normally transmit the digest output to a third-party by email or to an API endpoint when a `IngestDigest` workflow is executed.

You can trigger a silent `IngestDigest` workflow, which still validates the input and replaces existing digest data in eLife buckets, but avoids sending a digest to the third-party, by altering the file name of the digest zip file.

To start a silent digest workflow, make sure the zip file name ends with `-silent.zip` (with case insensitive matching, so it can be `-silent.zip` or `-SILENT.zip`), and copy that file to the digest input bucket.


## Installation and tests

eLife bot is currently configured and deployed by eLife builder libraries.

We have added unit tests for the eLife bot activities using Python unittest library. Running on the command line:
cd to elife-bot and execute:
python -m pytest --junitxml=build/junit.xml tests/


## Extending eLife bot with a new workflow

In principle this system can be extended horizontally. Adding new workers and workflows should be easy. 


## Tip using starter to execute and workflow

To start a workflow execution manually, for the starter to import the modules it requires, add `PYTHONPATH` to the invocation. For example, from the `elife-bot` root directory:

```
PYTHONPATH=. python starter/starter_Ping.py -e dev
```

## Issues and Backlog

Issues and backlog items are stored in Github on the [project issues page][pip].

Major milestones that we would like to see are:

- setting up deployment
- making extending the workflow super easy
- adding a visual reporting strucutre
- adding a way to poll external endpoints for ALM data (potentially)

[pip]: https://github.com/elifesciences/elife-bot/issues?labels=2+-+Working&milestone=2&state=open



## Contributing to the project

If you have a contribution you would like us to consider, please send a pull request. 


## Other eLife Resources

This is part of the eLife suite of tools. You can find more resources at [elifesciences.org](elifesciences.org).


## About eLife

eLife is an open access publisher in the life sciences. We are supported by [The Wellcome Trust](http://www.wellcome.ac.uk/), [The Howard Hughes Medical Institute](http://www.hhmi.org/) and [The Max Planck Society](http://www.mpg.de/en). We publish at [elifescience.org](http://elifesciences.org/).

# Copyright & Licence

Copyright 2016 eLife Sciences. Licensed under the [MIT license](LICENSE).
