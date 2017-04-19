import provider.imageresize as resizer
from provider.storage_provider import StorageContext
from mimetypes import guess_type


def generate_images(settings, formats, fp, info, publish_locations, logger):
        try:
            for format_spec_name in formats:
                format_spec = formats[format_spec_name]
                # if sources not present or includes file extension for this image
                if 'sources' not in format_spec or info.extension in [
                        x.strip() for x in format_spec['sources'].split(',')]:
                    download = 'download' in format_spec and format_spec['download']
                    fp.seek(0)  # rewind the tape
                    filename, image = resizer.resize(format_spec, fp, info, logger)
                    if filename is not None and image is not None:
                        store_in_publish_locations(settings, filename, image, publish_locations, download)
                        logger.info("Stored image %s as %s" % (filename, str(publish_locations)))
                    else:
                        raise RuntimeError("filename or image is None. resizer.resize problem.")
        finally:
            fp.close()


def store_in_publish_locations(settings, filename, image, publish_locations, download):
        try:
            storage_context = StorageContext(settings)

            for resource in publish_locations:
                image.seek(0)
                content_type, encoding = guess_type(filename)
                storage_context.set_resource_from_file(resource + filename, image, metadata={'Content-Type': content_type})

                if download:
                    dict_metadata = {'Content-Disposition':
                                     str("Content-Disposition: attachment; filename=" + filename + ";"),
                                     'Content-Type': content_type}
                    filename_no_extension, extension = filename.rsplit('.', 1)
                    file_download = filename_no_extension + "-download." + extension
                    storage_context.copy_resource(resource + filename, resource + file_download,
                                                  additional_dict_metadata=dict_metadata)

        finally:
            image.close()