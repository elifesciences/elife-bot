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
    
    
## Amazon SWF workflow notes

* Deciders will handle more than the default 100 event history items returned by one polling request to SWF by following nextPageTokens until the complete event history is assembled.

## Simple DB notes (pulled in from Graham)

# SimpleDB basics

SimpleDB is a non-relational object data store provided as a service by Amazon. It is intended for small amounts of data.

There is no interface for SimpleDB in the Amazon web console, and the user must rely on programmatic methods of access. One way to browse the data for development purposes is using the Javascript Scratchpad provided by Amazon. Code libraries also provide access, such as boto for Python.

* [Get Started with Amazon SimpleDB](http://docs.aws.amazon.com/AmazonSimpleDB/2009-04-15/GettingStartedGuide/Welcome.html)
* [Javascript Scratchpad for Amazon SimpleDB](http://aws.amazon.com/code/1137?_encoding=UTF8&jiveRedirect=1)
* [Amazon SimpleDB Developer Guide ](http://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/using.html)

### Why SimpleDB?

While the eLife bot is mostly made from stateless components, it was deemed beneficial to store the result of some activities in a persistent way. SimpleDB is fast, highly available and provided as a service that Amazon manages. The non-relational model makes it flexible to adapt to future schema changes. The ``boto`` library provides a simple object mapping functions that are very convenient when used appropriately.

### Scratchpad quickstart in the S3 monitor context

The getting started guide is recommended reading, and references the Scratchpad in the examples.

1. Download and extract the scratchpad files
2. Run in the browser, e.g. use python:
```
cd AmazonSimpleDB-2009-04-15-scratchpad/webapp
python -m SimpleHTTPServer 8000
```
3. Browse to http://localhost:8000/
4. Enter your AWS Access Key ID and AWS Secret Access Key

Some examples: if you ``ListDomains``, max number of domains 10 (for example) and invoke request, a new window will open and display something like the following:

```
<ListDomainsResponse xmlns="http://sdb.amazonaws.com/doc/2009-04-15/">
<ListDomainsResult>
<DomainName>S3File</DomainName>
<DomainName>S3FileLog</DomainName>
<DomainName>S3FileLog_dev</DomainName>
<DomainName>S3File_dev</DomainName>
</ListDomainsResult>
<ResponseMetadata>
<RequestId>77c3a0d3-47e3-ea74-5d3a-329447232853</RequestId>
<BoxUsage>0.0000071759</BoxUsage>
</ResponseMetadata>
</ListDomainsResponse>
```

Domains are like tables in traditional databases.

Another example, if you choose ``DomainMetadata``, domain name S3File it reports there are 837 items stored as well as other details:

```
<DomainMetadataResponse xmlns="http://sdb.amazonaws.com/doc/2009-04-15/">
<DomainMetadataResult>
<ItemCount>837</ItemCount>
<ItemNamesSizeBytes>33026</ItemNamesSizeBytes>
<AttributeNameCount>22</AttributeNameCount>
<AttributeNamesSizeBytes>284</AttributeNamesSizeBytes>
<AttributeValueCount>18222</AttributeValueCount>
<AttributeValuesSizeBytes>304978</AttributeValuesSizeBytes>
<Timestamp>1373668029</Timestamp>
</DomainMetadataResult>
<ResponseMetadata>
<RequestId>830107c0-1474-8885-68cd-000fb6d3bc6d</RequestId>
<BoxUsage>0.0000071759</BoxUsage>
</ResponseMetadata>
</DomainMetadataResponse>
```

Try ``DomainMetadata`` on the S3FileLog domain:

```
<DomainMetadataResponse xmlns="http://sdb.amazonaws.com/doc/2009-04-15/">
<DomainMetadataResult>
<ItemCount>840</ItemCount>
<ItemNamesSizeBytes>42401</ItemNamesSizeBytes>
<AttributeNameCount>22</AttributeNameCount>
<AttributeNamesSizeBytes>284</AttributeNamesSizeBytes>
<AttributeValueCount>18288</AttributeValueCount>
<AttributeValuesSizeBytes>305524</AttributeValuesSizeBytes>
<Timestamp>1373668300</Timestamp>
</DomainMetadataResult>
<ResponseMetadata>
<RequestId>f44dd156-5a82-f742-b89f-e6b4ca24c583</RequestId>
<BoxUsage>0.0000071759</BoxUsage>
</ResponseMetadata>
</DomainMetadataResponse>
```

There are 3 more items in the ``S3FileLog`` domain than in the ``S3File`` domain. This would indicate three S3 files have been modified over the operation of the S3 monitor, resulting in a new log table entry when the modification was discovered.

**Do not** issue a ``DeleteDomain``, that would delete the data and there is no backup. Although the data will be recreated from the current state of S3 files in the monitoring system, the log of files it has seen over time will be lost.

# S3Monitor activity

### S3Monitor in a nutshell

1. Currently, each hour at the top of the hour, the S3Monitor workflow is run, and consequently the S3Monitor activity.
2. A worker polls the ``elife-articles`` S3 bucket for objects.
3. Items in the ``S3File`` SimpleDB domain are either a) modified if they already exist for the object's key, or b) a new item is added if the key does not already exist
4. Additionally, items in the ``S3FileLog`` domain are added if they did not already exist. Except, if an existing S3 object has been modified, a **new** log item is added. In doing so, a record of each modification of the file is recorded.
5. Done! The SimpleDB data is now ready to provide data to other workflows.

Gotchas and notes:

* The monitor is currently only single threaded, and takes a couple minutes on EC2 for under a thousand S3 objects. For a larger set of buckets, the process would be faster if split into parallel polling
* While the S3Monitor is running, you cannot be sure the SimpleDB data is fully reflecting the S3 bucket (since it hasn't finished polling yet).
* If an object in S3 is modified more than once between S3Monitor polling occurrences, then the S3Monitor will not log the modification time it was not able to record.
* If an object in S3 is modified while the S3Monitor is running, then the modification will not be recorded until the next time the S3Monitor is run, if the object was already polled prior to the modification.

Phew!

### Use cases

Given the standard meta data recorded in the ``S3File`` and ``S3FileLog`` SimpleDB domains by the S3Monitor activity, we want to get:

* the most recent S3 objects for each eLife article that stores the a) article XML, b) images, c) PDF, d) supplementary files or e) video
* all the S3 objects for a particular eLife article, given the unique five digits in the DOI
* all the files updated since datetime X, optionally only returning the XML or PDF objects, for example

This is made possible in the eLife bot ``/provider/simpleDB.py`` data provider. It understands the SimpleDB schema, and the eLife object types (determined by object name string pattern matching) to return just what you want. The method in the provider to get the data is:

```
def elife_get_article_S3_file_items(self, file_data_type = None, doi_id = None, last_updated_since = None, latest = None):
```

# SimpleDB schemas

The current schemas in use for the S3Monitor are a domain for the current S3 bucket objects (``S3File`` and ``S3File_dev`` for the dev environment) and a domain for logging modifications to S3 objects (``S3FileLog`` adn ``S3FileLog_dev``). Both schemas are similar except log domain items will have a concatenated unique item name made up of the modified timestamp + item_name. For example,

* In the ``S3File`` domain, an item may have a unique name such as ``elife-articles/00003/elife00003.xml``
* For the ``S3FileLog`` domain to create unique names for each time a modification date is recorded, an item will have a name like ``1359244240_elife-articles/00003/elife00003.xml``

Using the scratchpad, you can query for a single item with the following ``Select`` Select Expression:

```
select * from S3File where item_name = 'elife-articles/00003/elife00003.xml'
```

Returning:

```
<SelectResponse xmlns="http://sdb.amazonaws.com/doc/2009-04-15/">
<SelectResult>
<Item>
<Name>elife-articles/00003/elife00003.xml</Name>
<Attribute>
<Name>bucket_name</Name>
<Value>elife-articles</Value>
</Attribute>
<Attribute>
<Name>_runtime_date</Name>
<Value>2013-07-12T23:00:03.000Z</Value>
</Attribute>
<Attribute>
<Name>item_name</Name>
<Value>elife-articles/00003/elife00003.xml</Value>
</Attribute>
<Attribute>
<Name>_runtime_time</Name>
<Value>23:00:03</Value>
</Attribute>
<Attribute>
<Name>_runtime_day</Name>
<Value>12</Value>
</Attribute>
<Attribute>
<Name>_runtime_month</Name>
<Value>07</Value>
</Attribute>
<Attribute>
<Name>_runtime_year</Name>
<Value>2013</Value>
</Attribute>
<Attribute>
<Name>_runtime_timestamp</Name>
<Value>1373670003</Value>
</Attribute>
<Attribute>
<Name>etag</Name>
<Value>"39a4a0a971af41c94bf4536f398e4be0"</Value>
</Attribute>
<Attribute>
<Name>last_modified_day</Name>
<Value>26</Value>
</Attribute>
<Attribute>
<Name>last_modified_timestamp</Name>
<Value>1359244240</Value>
</Attribute>
<Attribute>
<Name>last_modified</Name>
<Value>2013-01-26T23:50:40.000Z</Value>
</Attribute>
<Attribute>
<Name>last_modified_date</Name>
<Value>2013-01-26T23:50:40.000Z</Value>
</Attribute>
<Attribute>
<Name>last_modified_month</Name>
<Value>01</Value>
</Attribute>
<Attribute>
<Name>last_modified_year</Name>
<Value>2013</Value>
</Attribute>
<Attribute>
<Name>last_modified_time</Name>
<Value>23:50:40</Value>
</Attribute>
<Attribute>
<Name>name</Name>
<Value>00003/elife00003.xml</Value>
</Attribute>
<Attribute>
<Name>owner</Name>
<Value><boto.s3.user.User instance at 0x205d950></Value>
</Attribute>
<Attribute>
<Name>storage_class</Name>
<Value>STANDARD</Value>
</Attribute>
<Attribute>
<Name>content_type</Name>
<Value>application/octet-stream</Value>
</Attribute>
<Attribute>
<Name>log_item_name</Name>
<Value>1359244240_elife-articles/00003/elife00003.xml</Value>
</Attribute>
<Attribute>
<Name>size</Name>
<Value>120896</Value>
</Attribute>
</Item>
</SelectResult>
<ResponseMetadata>
<RequestId>8696989e-8afa-d4ca-0036-bf0eeb91be88</RequestId>
<BoxUsage>0.0000228616</BoxUsage>
</ResponseMetadata>
</SelectResponse>
```

The SimpleDB item attributes currently stored by the S3Monitor for each S3 object:

```
bucket_name
item_name
etag
name
owner
storage_class
content_type
log_item_name
size
last_modified
_runtime_date
_runtime_timestamp
_runtime_time
_runtime_day
_runtime_month
_runtime_year
last_modified_date
last_modified_timestamp
last_modified_time
last_modified_day
last_modified_month
last_modified_year
```