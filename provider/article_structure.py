import re
import datetime


class ArticleInfo(object):
    """
    Determine useful information about an article file from its filename
    see https://github.com/elifesciences/ppp-project/blob/master/file_naming_spec.md
    for more information on the naming specification and further definition of
    properties below

    full_filename: the full name of the file including extension
    filename: the name without the file extension
    extension: the file extension
    is_article_zip: boolean, if the file is a zip of a complete article
    status: the status (e.g. vor) if file is a zip of a complete article, else None
    file_type: a string representing a logical type for the file. Values are:
        - ArticleZip: file is a zip of a complete article
        - Figure: file is a tiff image for a figure
        - Other: file is something else
        (more required!)
    journal: the name of the journal (e.g. elife)
    article_id: referred to in the naming spec as the file id (f-id) of the article the file is part of (e.g. 00012)
    versioned: boolean representing if the file has a version number
    version: the version of the file (or None if not versioned)
    extra-info: the parts of the filename between the f-id (or status if present) and the version (if present) or extension
    """

    def __init__(self, full_filename):
        self.full_filename = full_filename

        # TODO : check full_filename matches basic validation regex for:
        # `elife-<f-id>-<status>(-<asset><a-id>)(-<sub-asset><sa-id>)(-<data><d-id>)(-<code><c-id>)
        # (-<media><m-id>)(-<reporting standard><repstand-id>)(-<supplementary file><supp-id>)|(-v<version>).<ext>`
        # including minimum required info of f-id, status and ext.

        (self.filename, self.extension) = full_filename.rsplit('.', 1)
        parts = self.filename.split('-')

        match = re.match('.*?-[0-9]+?-(poa|vor)(-*?(v|r)[0-9]+?)?(-([0-9]+))?\.zip', self.full_filename, re.IGNORECASE)
        first_other_index = 2
        if match is not None:
            self.status = match.group(1)
            self.is_article_zip = True
            first_other_index = 3
        else:
            self.status = None
            self.is_article_zip = False
            # TODO : determine other useful file_type values from extra_info list if required

        # Files in PoA 04493 do not have hyphenated names so handle it now before continuing
        if len(parts) < 2:
            self.file_type = None
            return

        self.journal = parts[0]
        self.article_id = parts[1]
        last_part_index = len(parts) - 1
        last_part = parts[last_part_index]
        if last_part.startswith('v') and not last_part.startswith('video'):
            self.versioned = True
            self.version = last_part[1:]
            last_part_index -= 1
        else:
            self.versioned = False
            self.version = None
        self.extra_info = parts[first_other_index:last_part_index + 1]

        if self.is_article_zip:
            self.file_type = "ArticleZip"
        elif (len(self.extra_info) > 0
              and (self.extra_info[-1].startswith('video')
                   or self.extra_info[-1].startswith('code'))):
            self.file_type = 'Other'
        elif (len(self.extra_info) > 0
              and (self.extra_info[0].startswith('fig')
                   or self.extra_info[0].startswith('figsupp'))
              and not self.extra_info[0].startswith('figures')):
            self.file_type = "Figure"
        elif len(self.extra_info) > 1 and self.extra_info[0].startswith('resp') and self.extra_info[1].startswith('fig'):
            self.file_type = "Figure"
        elif len(self.extra_info) > 1 and self.extra_info[0].startswith('app') and self.extra_info[1].startswith('fig'):
            self.file_type = "Figure"
        elif len(self.extra_info) > 1 and self.extra_info[0].startswith('box') and self.extra_info[1].startswith('fig'):
            self.file_type = "Figure"
        elif len(self.extra_info) > 0 and self.extra_info[0].startswith('inf'):
            self.file_type = "Inline"
        elif len(parts) == 3 and self.extension == 'xml':
            self.file_type = 'ArticleXML'
        else:
            self.file_type = 'Other'

    def get_update_date_from_zip_filename(self):
        filename = self.full_filename
        m = re.search(ur'.*?-.*?-.*?-.*?-(.*?)\..*', filename)
        if m is None:
            return None
        else:
            try:
                raw_update_date = m.group(1)
                updated_date = datetime.datetime.strptime(raw_update_date, "%Y%m%d%H%M%S")
                return updated_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                return None

    def get_version_from_zip_filename(self):
        filename = self.full_filename
        m = re.search(ur'-v([0-9]+?)[\.|-]', filename)
        if m is None:
            return None
        else:
            return m.group(1)

def article_figure(file):
    article_info = ArticleInfo(file)
    return article_info.file_type == "Figure"

def has_extensions(file, extensions):
    article_info = ArticleInfo(file)
    return article_info.extension in extensions


def get_original_files(files):
    regex = re.compile(ur'-v([0-9])[\.]')
    fs = list(filter(regex.search, files))
    return fs

def get_figures_for_iiif(files):
    # should only be tif
    originals_figures_tif = [f for f in get_original_files(files) if (article_figure(f) and has_extensions(f, ['tif']))]
    fs = originals_figures_tif + get_media_file_images(files)
    return fs


def file_parts(filename):
    prefix = filename.split('.')[0]
    extension = filename.split('.')[-1]
    return prefix, extension


def get_media_file_images(files):
    return list(filter(lambda f: is_media_file(f) and has_extensions(f, ['jpg']), files))


def is_media_file(filename):
    (file_prefix, file_extension) = file_parts(filename)
    file_type_plus_index = file_prefix.split('-')[-1]
    if ("media" in file_type_plus_index) or ("video" in file_type_plus_index):
        return True
    else:
        return False


def main():
    a = ArticleInfo("elife-00012-fig3-figsupp1-data2.csv")
    print a


if __name__ == '__main__':
    main()
