=======
elife-bot
=========

tools for creating an automatic publishing workflow. 

# Project dependencies (planned)

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

# Roadmap

1. Poll eLife s3 bucket for new and updated objects, especially XML.
2. Decoupled tasks to run via Amazon Simple Workflow (SWF)

# Local development with Vagrant

At the time of this writing, Vagrant using Chef Solo is used to configure a local virtual machine with standard attributes for development. Cookbooks, recipes and roles for Chef are included in the repository to load locally.

## Initial config (done once)

1. Download and install [Vagrant][vagrant].
2. Define the base box (should download the machine image just once and then be reused):

    vagrant box add base http://files.vagrantup.com/lucid32.box

## Running Vagrant VM

1. Go into /vagrant directory in console.
2. Run

    vagrant up

3. Normal loading may take about 2-3 minutes.
4. When completed, you can login via [SSH][vagrant_ssh]

    vagrant ssh

5. Simple test, using API prototype code:
    
    git clone git://github.com/elifesciences/elife-api-prototype.git
    cd elife-api-prototype
    cp settings-example.py settings.py
    cd tests
    lettuce

6. To stop the VM, in console:

    vagrant destroy


[vagrant]: http://www.vagrantup.com/
[vagrant_ssh]: http://docs.vagrantup.com/v1/docs/getting-started/ssh.html