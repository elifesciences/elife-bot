import re
import datetime


class ArticleInfo:
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
    article_id: referred to in the naming spec as the file id (f-id) of the
        article the file is part of (e.g. 00012)
    versioned: boolean representing if the file has a version number
    version: the version of the file (or None if not versioned)
    extra-info: the parts of the filename between the f-id (or status if present) and
        the version (if present) or extension
    """

    def __init__(self, full_filename):
        self.full_filename = full_filename

        # TODO : check full_filename matches basic validation regex for:
        # `elife-<f-id>-<status>(-<asset><a-id>)(-<sub-asset><sa-id>)(-<data><d-id>)(-<code><c-id>)
        # (-<media><m-id>)(-<reporting standard><repstand-id>)
        # (-<supplementary file><supp-id>)|(-v<version>).<ext>`
        # including minimum required info of f-id, status and ext.

        (self.filename, self.extension) = full_filename.rsplit(".", 1)
        parts = self.filename.split("-")

        match = re.match(
            r".*?-[a-zA-Z0-9]+?-(poa|vor)(-*?(v|r)[0-9]+?)?(-([0-9]+))?\.zip",
            self.full_filename,
            re.IGNORECASE,
        )
        first_other_index = 2
        if match is not None:
            self.status = match.group(1)
            self.is_article_zip = True
            first_other_index = 3
        else:
            self.status = None
            self.is_article_zip = False

        # Files in PoA 04493 do not have hyphenated names so handle it now before continuing
        if len(parts) < 2:
            self.file_type = None
            return

        self.journal = parts[0]
        self.article_id = parts[1]
        last_part_index = len(parts) - 1
        last_part = parts[last_part_index]
        if last_part.startswith("v") and not last_part.startswith("video"):
            self.versioned = True
            self.version = last_part[1:]
            last_part_index -= 1
        else:
            self.versioned = False
            self.version = None
        self.extra_info = parts[first_other_index : last_part_index + 1]

        self.file_type = "Other"  # default type
        if self.is_article_zip:
            self.file_type = "ArticleZip"
        elif (
            len(parts) == 2 or (len(parts) == 3 and not self.extra_info)
        ) and self.extension == "xml":
            self.file_type = "ArticleXML"
        elif self.extra_info:
            # extra file parts
            parent_name = self.extra_info[0]
            child_name = ""
            if len(self.extra_info) > 1:
                child_name = self.extra_info[1]
            final_name = self.extra_info[-1]
            # determine the file_type based on the extra file parts
            if parent_name.startswith("resp") and final_name.startswith("fig"):
                self.file_type = "Figure"
            elif parent_name.startswith("sa") and final_name.startswith("fig"):
                self.file_type = "Figure"
            elif parent_name.startswith("app") and final_name.startswith("fig"):
                self.file_type = "Figure"
            elif parent_name.startswith("box") and final_name.startswith("fig"):
                self.file_type = "Figure"
            elif parent_name.startswith("chem") and final_name.startswith("fig"):
                self.file_type = "Figure"
            elif parent_name.startswith("scheme") and final_name.startswith("fig"):
                self.file_type = "Figure"
            elif final_name.startswith("video") or final_name.startswith("code"):
                self.file_type = "Other"
            elif parent_name.startswith("figures"):
                self.file_type = "FigurePDF"
            elif (
                parent_name.startswith("fig") or parent_name.startswith("figsupp")
            ) and not parent_name.startswith("figures"):
                self.file_type = "Figure"
            elif parent_name.startswith("inf"):
                self.file_type = "Inline"

    def get_update_date_from_zip_filename(self):
        filename = self.full_filename
        match = re.search(r".*?-.*?-.*?-.*?-(.*?)\..*", filename)
        if match is None:
            return None
        try:
            raw_update_date = match.group(1)
            updated_date = datetime.datetime.strptime(raw_update_date, "%Y%m%d%H%M%S")
            return updated_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        except:
            return None

    def get_version_from_zip_filename(self):
        filename = self.full_filename
        match = re.search(r"-v([0-9]+?)[\.|-]", filename)
        if match is None:
            return None
        return match.group(1)


def article_figure(filename):
    article_info = ArticleInfo(filename)
    return article_info.file_type == "Figure"


def figure_pdf(filename):
    article_info = ArticleInfo(filename)
    return article_info.file_type == "FigurePDF"


def inline_figure(filename):
    article_info = ArticleInfo(filename)
    return article_info.file_type == "Inline"


def has_extensions(filename, extensions):
    article_info = ArticleInfo(filename)
    return article_info.extension in extensions


def get_original_files(files):
    regex = re.compile(r"-v([0-9]+)[\.]")
    file_list = list(filter(regex.search, files))
    return file_list


def get_figures_for_iiif(files):
    # should only be tif
    originals_figures_tif = [
        f
        for f in get_original_files(files)
        if article_figure(f) and has_extensions(f, ["tif"])
    ]
    file_list = originals_figures_tif + get_media_file_images(files)
    return file_list


def get_inline_figures_for_iiif(files):
    # should only be tif
    "return a list of all inline figure files"
    return [
        f
        for f in get_original_files(files)
        if inline_figure(f) and has_extensions(f, ["tif"])
    ]


def get_figures_pdfs(files):
    return [f for f in files if figure_pdf(f) and has_extensions(f, ["pdf"])]


def get_videos(files):
    return [f for f in files if is_video_file(f)]


def file_parts(filename):
    """
    prefix is part before the first dot
    extension is all the parts after the first dot
    """
    prefix = filename.split(".")[0]
    extension = ".".join(filename.split(".")[1:]).lstrip(".")
    return prefix, extension


def get_media_file_images(files):
    return [f for f in files if is_video_file(f) and has_extensions(f, ["jpg"])]


def is_video_file(filename):
    """
    Simple check for video file names
    E.g. match True on elife-00005-media1.mov
         match True on elife-99999-resp-media1.avi
         match False on elife-00005-media1-code1.wrl
    """

    file_prefix, file_extension = file_parts(filename)
    file_type_plus_index = file_prefix.split("-")[-1]
    return bool("media" in file_type_plus_index or "video" in file_type_plus_index)


def pre_ingest_assets(files):
    original_figures = get_figures_for_iiif(files)
    inline_figures = get_inline_figures_for_iiif(files)
    iiif_assets = original_figures + inline_figures + get_videos(files)
    pdf_figures = get_figures_pdfs(files)
    return list(set(iiif_assets + pdf_figures))


def get_article_xml_key(bucket, expanded_folder_name):
    """
    locate the article XML file in the expanded article bucket on S3
    and return the S3 key and the filename of the object
    """
    files = bucket.list(expanded_folder_name + "/", "/")
    for bucket_file in files:
        key = bucket.get_key(bucket_file.key)
        filename = key.name.rsplit("/", 1)[1]
        info = ArticleInfo(filename)
        if info.file_type == "ArticleXML":
            return key, filename
    return None, None


def main():
    article = ArticleInfo("elife-00012-fig3-figsupp1-data2.csv")
    print(article)


if __name__ == "__main__":
    main()
