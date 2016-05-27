from datetime import datetime
from jinja2 import Template
from os import path
from zipfile import ZipFile

def article_zip():
    template = "elife-15893.template.xml.jinja"
    id = datetime.now().strftime("%Y%m%d%H%M%S")
    current_directory = path.dirname(__file__)
    with open(current_directory + '/' + template, 'r') as template_file:
        data = template_file.read().decode('UTF-8')
    template = Template(data)
    xml_content = template.render(article = { 'id': id })
    xml_filename = '/tmp/elife-%s.xml' % id
    with open(xml_filename, 'w') as xml_file:
        xml_file.write(xml_content.encode('utf-8'))
    zip_filename = '/tmp/elife-%s-vor-r1.zip' % id
    with ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write(xml_filename, path.basename(xml_filename))
    return ArticleZip(id, zip_filename)

class ArticleZip:
    def __init__(self, id, filename):
        self._id = id
        self._filename = filename

    def id(self):
        return self._id

    def doi(self):
        return '10.7554/eLife.' + self._id

    def filename(self):
        return self._filename
