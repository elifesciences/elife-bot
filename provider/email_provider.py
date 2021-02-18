"provider for sending email"
import os
import smtplib
import unicodedata
import traceback
from collections import OrderedDict
from string import Template
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import boto.ses
from provider.utils import bytes_decode, unicode_encode


def ses_connect(settings):
    "connect to SES"
    return boto.ses.connect_to_region(
        settings.ses_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key)


def smtp_setting(settings, name):
    "return the property from the settings object otherwise return None"
    if hasattr(settings, name):
        return getattr(settings, name)
    return None


def smtp_connect(settings, logger=None):
    "connect to SMTP"
    smtp_host = smtp_setting(settings, 'smtp_host')
    smtp_port = smtp_setting(settings, 'smtp_port')
    smtp_starttls = smtp_setting(settings, 'smtp_starttls')
    smtp_ssl = smtp_setting(settings, 'smtp_ssl')
    smtp_username = smtp_setting(settings, 'smtp_username')
    smtp_password = smtp_setting(settings, 'smtp_password')
    try:
        connection = (smtplib.SMTP_SSL(smtp_host, smtp_port)
                      if smtp_ssl else smtplib.SMTP(smtp_host, smtp_port))
    except:
        connection = None
        if logger:
            logger.error('error in smtp_connect: %s ', traceback.format_exc())
    if smtp_starttls:
        connection.starttls()
    if smtp_username and smtp_password:
        connection.login(smtp_username, smtp_password)
    return connection


def encode_filename(file_name):
    """consistently encode a file name in unicode

    Discovered trying to get a consistent file name from the file system on
    multiple operating systems, if test pass on MacOS they will not necessarily
    pass on Linux, for example. Using unicodedata normalize here in this function
    it will return a consistent unicode file name. Note: this is being used for
    setting the file name of an email attachment, whereas the original file name
    from the local file system is still used to open the file from disk.

    Inspired by the answer
    https://stackoverflow.com/a/9758019
    with some adaptations using the encoding and decoding utility functions in this project

    See also
    https://docs.python.org/3/library/unicodedata.html?highlight=unicodedata
    """
    if file_name is None:
        return file_name
    return unicode_encode(bytes_decode(
        unicodedata.ucd_3_2_0.normalize('NFC', bytes_decode(file_name))))


def attachment(file_name,
               media_type='vnd.openxmlformats-officedocument.wordprocessingml.document',
               charset='utf-8'):
    "create an attachment from the file"
    attachment_name = encode_filename(os.path.split(file_name)[-1])
    with open(file_name, 'rb') as open_file:
        email_attachment = MIMEApplication(
            open_file.read(), media_type, name=(charset, '', attachment_name))
    email_attachment.add_header(
        'Content-Disposition', 'attachment',
        filename=(charset, '', attachment_name))
    return email_attachment


def add_attachment(message, file_name,
                   media_type='vnd.openxmlformats-officedocument.wordprocessingml.document',
                   charset='utf-8'):
    "add an attachment to the message"
    email_attachment = attachment(file_name, media_type, charset)
    message.attach(email_attachment)


def add_text(message, text, subtype='plain', charset='utf-8'):
    "add text to the message"
    message.attach(MIMEText(text, subtype, charset))


def message(subject, sender, recipient, bcc=None):
    "create an email message to later attach things to"
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    if bcc:
        message['BCC'] = bcc
    return message


def ses_send(connection, sender, recipient, message):
    "send a MIMEMultipart email to the recipient from sender"
    return connection.send_raw_email(message.as_string(), source=sender, destinations=recipient)


def smtp_send(connection, sender, recipient, message, logger=None):
    "send a MIMEMultipart email to the recipient from sender by SMTP"
    try:
        connection.sendmail(sender, recipient, message.as_string())
    except smtplib.SMTPSenderRefused:
        if logger:
            logger.error('error in smtp_send: %s ', traceback.format_exc())
        return False
    return True


def smtp_send_message(connection, email_message, logger=None):
    """send the email message using the connection"""
    sender = email_message.get('From')
    recipient = email_message.get('To')
    # if there is a BCC address, add them to the recipient list
    if email_message.get('BCC'):
        if isinstance(recipient, str):
            recipient = [recipient]
        recipient.append(email_message.get('BCC'))
    return smtp_send(connection, sender, recipient, email_message, logger)


def smtp_send_messages(settings, messages, logger=None):
    """send a list of messages on the connection"""
    connection = smtp_connect(settings, logger)
    details = OrderedDict([("error", 0), ("success", 0)])
    for email_message in messages:
        result = smtp_send_message(connection, email_message, logger)
        if result:
            details["success"] += 1
        else:
            details["error"] += 1
    return details


def simple_message(sender, recipient, subject, body, subtype='plain',
                   charset='utf-8', attachments=None, logger=None, bcc=None):
    """set values of a message

    :param sender: email address of the sender
    :param recipient: email address of the recipient
    :param subject: email subject
    :param body: email body
    :param subtype: body text subtype, typically plain or html
    :param charset: charset for the body text
    :param attachments: optional list of email attachments, each a file system path to the file
    :param logger: optional log.logger object
    :param bcc: optional email address to BCC to
    :returns: MIMEMultipart email message object
    """
    email_message = message(subject, sender, recipient, bcc)
    add_text(email_message, body, subtype, charset)
    if attachments:
        for attachment in attachments:
            add_attachment(email_message, attachment)
    return email_message


def simple_messages(sender, recipients, subject, body, subtype='plain',
                   charset='utf-8', attachments=None, logger=None, bcc=None):
    """list of simple messages for a list of recipients

    :param sender: email address of the sender
    :param recipients: list of recipient email addresses
    :param subject: email subject
    :param body: email body
    :param subtype: body text subtype, typically plain or html
    :param charset: charset for the body text
    :param attachments: optional list of email attachments, each a file system path to the file
    :param logger: optional log.logger object
    :param bcc: optional email address to BCC to
    :returns: list of MIMEMultipart email message objects
    """
    messages = []
    for recipient in recipients:
        messages.append(simple_message(
            sender, recipient, subject, body, subtype=subtype, 
            charset=charset, attachments=attachments, logger=logger, bcc=bcc))
    return messages


def list_email_recipients(email_list):
    "return a list of email recipients from a string or list input"
    recipient_email_list = []
    # Handle multiple recipients, if specified
    if isinstance(email_list, list):
        for email in email_list:
            recipient_email_list.append(email)
    else:
        recipient_email_list.append(email_list)
    return recipient_email_list


def valid_recipient(recipient):
    """Check the recipient has a good email address

    :param recipient: dict or object for the recipient
    :returns: boolean True if valid
    """
    if isinstance(recipient, dict):
        return valid_recipient_dict(recipient)
    # if not a dict check as an object
    return valid_recipient_object(recipient)


def valid_recipient_dict(recipient):
    """Check the recipient dict has a good email address

    :param recipient: dict type with a key of e_mail in it
    :returns: boolean True if valid
    """
    if recipient is None:
        return False
    if "e_mail" not in recipient:
        return False
    if recipient.get("e_mail") is None:
        return False
    if recipient.get("e_mail") is not None and str(recipient.get("e_mail")).strip() == "":
        return False
    return True


def valid_recipient_object(recipient):
    """Check the recipient object has a good email address

    :param recipient: object with a property named e_mail
    :returns: boolean True if valid
    """
    if recipient is None:
        return False
    if not hasattr(recipient, 'e_mail'):
        return False
    if recipient.e_mail is None:
        return False
    if recipient.e_mail is not None and str(recipient.e_mail).strip() == "":
        return False
    return True


def get_admin_email_body_foot(activity_id, workflow_id, datetime_string, domain):
    """Format the footer of the body of the email"""
    string_template = None
    with open('template/admin_email_body_foot.txt', 'r') as open_file:
        string_template = Template(open_file.read())
    if string_template:
        return string_template.safe_substitute(
            activity_id=activity_id, workflow_id=workflow_id, datetime_string=datetime_string,
            domain=domain)
    return ''


def simple_email_body(datetime_string, body_content=''):
    """body of a simple success or error email"""
    string_template = None
    with open('template/simple_email_body.txt', 'r') as open_file:
        string_template = Template(open_file.read())
    if string_template:
        return string_template.safe_substitute(
            body_content=body_content,
            datetime_string=datetime_string)
    return ''
