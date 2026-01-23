import email
import os
import shutil
import zipfile
from digestparser.objects import Digest, Image
from provider import cleaner, meca, utils
from provider.article import article
from tests import list_files


def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def delete_folder(folder, recursively=False):
    if recursively:
        shutil.rmtree(folder)
    else:
        os.rmdir(folder)


def delete_files_in_folder(folder, filter_out=None):
    if not filter_out:
        filter_out = []
    file_list = os.listdir(folder)
    for file_name in file_list:
        if file_name in filter_out:
            continue
        path = folder + "/" + file_name
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            delete_folder(path, recursively=True)


def delete_directories_in_folder(folder):
    folder_list = os.listdir(folder)
    for dir_name in folder_list:
        dir_path = os.path.join(folder, dir_name)
        if os.path.isdir(dir_path):
            delete_folder(dir_path, True)


def delete_everything_in_folder(self, folder):
    self.delete_files_in_folder(folder)


def instantiate_article(article_type, doi, is_poa=None, was_ever_poa=None):
    "for testing purposes, generate an article object"
    article_object = article()
    article_object.article_type = article_type
    article_object.doi = doi
    article_object.doi_id = utils.pad_msid(utils.msid_from_doi(doi))
    article_object.is_poa = is_poa
    article_object.was_ever_poa = was_ever_poa
    return article_object


def create_digest(
    author=None, doi=None, text=None, title=None, image=None, summary=None
):
    "for testing generate a Digest object an populate it"
    digest_content = Digest()
    digest_content.author = author
    digest_content.doi = doi
    if text:
        digest_content.text = text
    if title:
        digest_content.title = title
    if image:
        digest_content.image = image
    if summary:
        digest_content.summary = summary
    return digest_content


def create_digest_image(caption=None, file_name=None):
    "for testing generate a Digest Image object an populate it"
    digest_image = Image()
    if caption:
        digest_image.caption = caption
    if file_name:
        digest_image.file = file_name
    return digest_image


def body_from_multipart_email_string(email_string):
    "Given a multipart email string, convert to Message and return decoded body"
    body = None
    email_message = email.message_from_string(email_string)
    if email_message.is_multipart():
        for payload in email_message.get_payload():
            body = payload.get_payload(decode=True)
    return body


IMAGE_FILE_PATH = "tests/files_source/digests/outbox/99999/digest-99999.jpg"


def figure_image_file_data(image_names):
    "data to add image files into a folder or meca zip for testing"
    file_details = []
    for image_name in image_names:
        details = {
            "file_path": IMAGE_FILE_PATH,
            "file_type": "figure",
            "upload_file_nm": image_name,
            "href": "content/%s" % image_name,
        }
        file_details.append(details)
    return file_details


def add_files_to_accepted_zip(zip_file_path, output_dir, file_details):
    "add files to a copy of an accepted submission zip file fixture"
    # create a temporary directory for zip repackaging
    zip_temp_dir = os.path.join(output_dir, "zip_temp_dir")
    os.mkdir(zip_temp_dir)

    zip_file_name = zip_file_path.rsplit(os.sep, 1)[-1]
    new_zip_file_path = os.path.join(output_dir, zip_file_name)
    new_zip_file_name = new_zip_file_path.rsplit(os.sep, 1)[-1]

    # extract the contents of the original zip
    with zipfile.ZipFile(zip_file_path) as open_zip:
        open_zip.extractall(zip_temp_dir)

    # zip file subfolder name and XML file path
    zip_sub_folder = new_zip_file_name.replace(".zip", "")
    zip_xml_file_path = "%s/%s.xml" % (zip_sub_folder, zip_sub_folder)

    # copy files to the zip sub folder
    for details in file_details:
        shutil.copy(
            details.get("file_path"),
            os.path.join(zip_temp_dir, zip_sub_folder, details.get("upload_file_nm")),
        )

    # modify the XML
    xml_path = os.path.join(zip_temp_dir, zip_xml_file_path)
    for details in file_details:
        # add file tag to the XML
        cleaner.add_file_tags_to_xml(xml_path, [details], identifier=zip_file_name)

    # create a new zip file, add the files from the folder to it
    with zipfile.ZipFile(new_zip_file_path, "w") as open_zip:
        for file_name in os.listdir(os.path.join(zip_temp_dir, zip_sub_folder)):
            file_path = "%s/%s" % (zip_sub_folder, file_name)
            open_zip.write(os.path.join(zip_temp_dir, file_path), file_path)

    # clean up the temporary directory
    shutil.rmtree(zip_temp_dir)

    return new_zip_file_path


def add_files_to_meca_zip(zip_file_path, output_dir, file_details):
    "add files to a copy of an MECA zip file fixture"
    # create a temporary directory for zip repackaging
    zip_temp_dir = os.path.join(output_dir, "zip_temp_dir")
    os.mkdir(zip_temp_dir)

    zip_file_name = zip_file_path.rsplit(os.sep, 1)[-1]
    new_zip_file_path = os.path.join(output_dir, zip_file_name)

    # extract the contents of the original zip
    with zipfile.ZipFile(zip_file_path) as open_zip:
        open_zip.extractall(zip_temp_dir)

    # zip file subfolder name and XML file path
    zip_xml_file_path = meca.get_meca_article_xml_path(
        zip_temp_dir, version_doi=None, caller_name=None, logger=None
    )

    zip_sub_folder = meca.meca_content_folder(zip_xml_file_path)

    # copy files to the zip sub folder
    for details in file_details:
        shutil.copy(
            details.get("file_path"),
            os.path.join(zip_temp_dir, zip_sub_folder, details.get("upload_file_nm")),
        )

    # modify the manuscript XML
    manuscript_xml_file_path = os.path.join(zip_temp_dir, "manifest.xml")
    # add file tag to the XML
    cleaner.add_item_tags_to_manifest_xml(
        manuscript_xml_file_path, file_details, identifier=zip_file_name
    )

    # create a new zip file, add the files from the folder to it
    with zipfile.ZipFile(new_zip_file_path, "w") as open_zip:
        for file_path in list_files(os.path.join(zip_temp_dir)):
            open_zip.write(os.path.join(zip_temp_dir, file_path), file_path)

    # clean up the temporary directory
    shutil.rmtree(zip_temp_dir)

    return new_zip_file_path


PDF_FIXTURE = "tests/files_source/elife-00353-v1.pdf"


def populate_meca_test_data(meca_file_path, session_dict, test_data, temp_dir):
    "for testing, repackage zip file and extract files into mock bucket folders"
    populated_data = {}

    # XML file paths
    populated_data["xml_file_name"] = session_dict.get("article_xml_path")
    populated_data["manifest_file_name"] = "manifest.xml"
    bucket_xml_file_path = os.path.join(
        temp_dir,
        session_dict.get("expanded_folder"),
        populated_data.get("xml_file_name"),
    )
    # create folders if they do not exist
    resource_folder = os.path.join(
        temp_dir,
        session_dict.get("expanded_folder"),
    )

    # create a new zip file fixture
    file_details = []
    if test_data.get("image_names"):
        file_details = figure_image_file_data(test_data.get("image_names"))
    new_zip_file_path = add_files_to_meca_zip(
        meca_file_path,
        temp_dir,
        file_details,
    )

    # unzip the test fixture files
    zip_file_paths = unzip_fixture(new_zip_file_path, resource_folder)
    populated_data["resources"] = [
        os.path.join(
            session_dict.get("expanded_folder"),
            file_path,
        )
        for file_path in zip_file_paths
    ]

    # add a generated PDF to the bucket
    if session_dict.get("pdf_s3_path"):
        pdf_resource_folder = os.path.join(
            temp_dir,
            os.path.dirname(session_dict.get("pdf_s3_path")),
        )
        os.makedirs(pdf_resource_folder, exist_ok=True)
        pdf_fixture = PDF_FIXTURE
        shutil.copy(
            pdf_fixture,
            os.path.join(temp_dir, session_dict.get("pdf_s3_path")),
        )
        populated_data["resources"].append(session_dict.get("pdf_s3_path"))

    # write additional XML to the XML file
    if test_data.get("sub_article_xml"):
        add_sub_article_xml(
            bucket_xml_file_path,
            test_data.get("sub_article_xml"),
        )

    return populated_data


def expanded_folder_resources(zip_file_path, directory):
    "expand the zip file to the directory and return a list resources"
    with zipfile.ZipFile(zip_file_path, "r") as open_zipfile:
        open_zipfile.extractall(path=directory)
        resources = open_zipfile.namelist()
    return resources


def expanded_folder_bucket_resources(directory, expanded_folder, zip_file_path):
    "populate the TempDirectory with files from zip_filename to mock a bucket folder in tests"
    if not os.path.exists(os.path.join(directory.path, expanded_folder)):
        directory.makedir(expanded_folder)
    directory_s3_folder_path = os.path.join(
        directory.path,
        expanded_folder,
    )
    resources = expanded_folder_resources(zip_file_path, directory_s3_folder_path)
    return resources


def populate_storage(from_dir, to_dir, filenames, sub_dir=""):
    "copy filesnames from from_dir to to_dir into the sub_dir for test bucket resources"
    resources = []
    for filename in filenames:
        from_filename = os.path.join(from_dir, filename)
        to_resource = os.path.join(sub_dir, filename)
        to_filename = os.path.join(to_dir, to_resource)
        resources.append(to_resource)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(to_filename), exist_ok=True)
        shutil.copy(from_filename, to_filename)
    return resources


def expanded_article_xml_path(xml_filename, parent_folder, expanded_folder):
    "get expanded submission test scenario XML path derived from naming convention"
    sub_folder = xml_filename.rsplit(".", 1)[0]
    return os.path.join(
        parent_folder,
        expanded_folder,
        sub_folder,
        xml_filename,
    )


def add_sub_article_xml(xml_path, sub_article_xml):
    "add XML to the end of the XML file article tag"
    with open(xml_path, "r", encoding="utf-8") as open_file:
        xml_string = open_file.read()
    with open(xml_path, "w", encoding="utf-8") as open_file:
        xml_string = xml_string.replace("</article>", "%s</article>" % sub_article_xml)
        open_file.write(xml_string)


def unzip_fixture(zip_file_path, folder_path):
    "unzip a zip and return file names"
    # create folders if they do not exist
    os.makedirs(folder_path, exist_ok=True)
    # unzip the test fixture files
    zip_file_paths = []
    with zipfile.ZipFile(zip_file_path, "r") as open_zipfile:
        for zipfile_info in open_zipfile.infolist():
            if zipfile_info.is_dir():
                continue
            open_zipfile.extract(zipfile_info, folder_path)
            zip_file_paths.append(zipfile_info.filename)
    return zip_file_paths
