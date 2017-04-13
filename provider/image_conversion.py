import provider.imageresize as resizer

def generate_images(formats, fp, info, cdn_path):
        # delegate this to module
        try:
            for format_spec_name in formats:
                format_spec = formats[format_spec_name]
                # if sources not present or includes file extension for this image
                if 'sources' not in format_spec or info.extension in [
                        x.strip() for x in format_spec['sources'].split(',')]:
                    download = 'download' in format_spec and format_spec['download']
                    fp.seek(0)  # rewind the tape
                    filename, image = resizer.resize(format_spec, fp, info, self.logger)
                    if filename is not None and image is not None:
                        self.store_in_cdn(filename, image, cdn_path, download)
                        self.logger.info("Stored image %s as %s" % (filename, cdn_path))
        finally:
            fp.close()