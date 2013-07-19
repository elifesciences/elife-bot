======
Installing and running eLife Bot
======

# Deploying to AWS.

Currently eLife bot is deployed manually using a snapshot of an Ec2 instance. 


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

Resave settings-example.py as settings.py, and enter your aws credentials.

Alternatively, place your AWS credentials in a file named .boto, or alternate method as specified at [Boto Config][botoc]

    [Credentials]
    aws_access_key_id = <your access key>
    aws_secret_access_key = <your secret key>

[botoc]: http://docs.pythonboto.org/en/latest/boto_config_tut.html

# Local development with Vagrant

Vagrant is used to configure a local virtual machine with standard attributes for development. See the
[elife-template-env][tmpl-env] repository for how to configure Vagrant.

[tmpl-env]: https://github.com/elifesciences/elife-template-env

1. Start a local virtual machine with Vagrant, as specified in [elife-template-env][tmpl-env]. Depending on the recipes run, it may pull code automatically from the "elife-bot" and "elife-api-prototype" repositories. If the repositories were not pulled automatically:

    git clone git://github.com/elifesciences/elife-api-prototype.git
    
    git clone git://github.com/elifesciences/elife-bot.git

2. To run tests, you must ensure the settings.py files exist and/or include the AWS credentials. At a minimum:

    cd elife-api-prototype
    
    cp settings-example.py settings.py
    
    cd elife-bot
    
    cp settings-example.py settings.py
    
    Edit the settings.py file to include your AWS credentials
    
3. Run tests:

    cd elife-bot/tests
    
    lettuce
    

