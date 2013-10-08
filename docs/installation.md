======
Installing and running eLife Bot
======

# Project dependencies

[Boto][bot] for AWS logic.
	
    $ pip install boto

[GitPython][gitpy] for git.
	
    $ easy_install gitpython

[Lettuce][let] for testing.
	
    $ pip install lettuce
	
[gitpy]: http://pypi.python.org/pypi/GitPython/
[bot]: http://www.crummy.com/software/BeautifulSoup/
[let]: http://packages.python.org/lettuce/

# Configure

Resave ``settings-example.py`` as ``settings.py``, and enter your AWS credentials.

Additionally, you may want to specify email addresses for the sending and receiving of admin emails from Amazon Simple Email Service (SES).

Note: To use write permissions in Fluidinfo workflow activities, you will also need to configure the ``settings.py`` file for the ``elife-api-prototype`` repository, as described below to include a valid Fluidinfo username and password with with write permissions on the namespace.

# Local development with Vagrant

Vagrant is used to configure a local virtual machine with standard attributes for development. See the
[elife-template-env][tmpl-env] repository for how to configure Vagrant.

[tmpl-env]: https://github.com/elifesciences/elife-template-env

1. Start a local virtual machine with Vagrant, as specified in [elife-template-env][tmpl-env]. Depending on the recipes run, it may pull code automatically from the "elife-bot" and "elife-api-prototype" repositories. If the repositories were not pulled automatically:

  ```
  git clone git://github.com/elifesciences/elife-api-prototype.git
  git clone git://github.com/elifesciences/elife-bot.git
  ```

2. To run tests, you must ensure the ``settings.py`` files exist and/or include the AWS credentials. At a minimum:

  ```
  cd elife-api-prototype
  cp settings-example.py settings.py
  cd elife-bot
  cp settings-example.py settings.py
  ```

  Edit the ``settings.py`` file to include your AWS credentials
    
3. Run tests:

  ```
  cd elife-bot/tests
  lettuce
  ```

# Deploying to AWS.

Currently eLife bot is deployed manually using a snapshot of an Ec2 instance. The Amazon Machine Image (AMI) is based on an Amazon Ubuntu image, and was built using [vagrant-aws][vagrant-aws] using eLife chef recipes.

[vagrant-aws]: https://github.com/mitchellh/vagrant-aws

Considering there is already a running Ec2 instance, deploying new code will likely happen on the running instance.

## When to deploy

__When deploying new code, try to do it between approximately 0:10 and 0:29 of the hour__. Due to the scheduled (cron) jobs, this is a time window when nothing is expected to be running. The S3Monitor is scheduled to run at :00 - the top of the hour - and you can watch for when it completes in order to stop the running system earlier than :10.

__Note 1__: The cron job, if present, will still be running ``cron.py`` every five minutes. You can suspend that prior to deployment if you think running it will do something disastrous.

__Note 2__: Workflow and activity classes are loaded dynamically. Settings and providers code, etc. are not. If you are only pulling in code for a workflow or activity, you do not need to stop the running ``worker.py`` and ``decider.py`` processes. The new workflow or activity code will be re-loaded the next time they are used.

## New code deployment procedure

In basic form, with respect to the running Ec2 instance and its current configuration:

1. SSH into the instance.

2. Stop all the worker and decider processes ((assuming no other python scripts are running that you need):

```
sudo killall -u root python
```

3. _Optionally_, stop the ``cron.py`` job from running every 5 minutes. This is curently not a requirement.

3. Pull in new code:

```
cd /home/localgit/elife-bot
sudo git pull origin master
```

4. _Optionally_, edit the ``settings.py`` file if they've changed or new ones were added since the last deployment.

5. Run the tests (sometimes optional if the deployment is minor):

```
cd /home/localgit/elife-bot/tests
sudo lettuce
```

If tests fail, attempt to fix, debug, troubleshoot, rollback in worst case scenario (?) as required.

6. Start workers and deciders:

```
cd /home/localgit/elife-bot
./scripts/run_micro.sh
```

A sample session deploying new code, without running tests:

```
ubuntu@domU:~$ cd /home/localgit
ubuntu@domU:/home/localgit$ cd elife-bot
ubuntu@domU:/home/localgit/elife-bot$ sudo killall -u root python
ubuntu@domU:/home/localgit/elife-bot$ sudo git pull origin master
remote: Counting objects: 14, done.
remote: Compressing objects: 100% (3/3), done.
remote: Total 9 (delta 6), reused 9 (delta 6)
Unpacking objects: 100% (9/9), done.
From git://github.com/elifesciences/elife-bot
 * branch            master     -> FETCH_HEAD
Updating 76bae20..ba2234f
Fast-forward
 cron.py                       |    2 +-
 starter/starter_PublishPDF.py |    2 +-
 starter/starter_PublishSVG.py |    2 +-
 3 files changed, 3 insertions(+), 3 deletions(-)
ubuntu@domU:/home/localgit/elife-bot$ ./scripts/run_micro.sh
ubuntu@domU:/home/localgit/elife-bot$ started decider thread
started worker thread
started worker thread
started decider thread
started decider thread
started worker thread
started worker thread
started decider thread
started decider thread
started worker thread
started worker thread
started decider thread
started worker thread
started worker thread
started worker thread
started worker thread

ubuntu@domU:/home/localgit/elife-bot$
```

# Troubleshooting scenarios

__Symptom__: Workflows are not running, you can login via SSH.
__Diagnosis__: The workers or deicders may have crashed.
__Solution__: Restart the workers and deciders.

1. Login to the instance via SSH as username "ubuntu" (with SSH key)
2. _Optionally_: check the diagnosis is correct:
```
ps aux | grep python
```
Some processes may be listed as <defunct>, or no processes are listed at all.

3. Restart the workers and deciders:
```
cd /home/localgit/elife-bot
sudo killall -u root python
./scripts/run_micro.sh
```

__Symptom__: Admin emails from the workflow have stopped, workflows are not running, you cannot login via SSH.
__Diagnosis__: The instance may have stopped / crashed.
__Solution__: Start the instance, then start workers and deciders.

1. Login to AWS web console.
2. Go to EC2.
3. Click on instances and start the stopped instance
4. Once started, continue with restarting the workers and deciders as described above.

__Symptom__: Workflows requiring disk fail but other workflows are completed
__Diagnosis__: The instance may have run a long time and the 8GB disk on the migroinstance is getting full / is full
__Solution__: Delete files from the tmp directory

1. Login to the instance via SSH as username "ubuntu" (with SSH key)
2. Check disk usage:
```
df
```
3. If full / getting full, delete the eLife bot tmp directory:
```
cd /home/localgit/elife-bot
sudo rm -Rf tmp
```




