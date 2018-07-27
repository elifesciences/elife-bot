from io import BytesIO

from wand.image import Image


def resize(format, filep, info, logger):

    image_buffer = None
    try:

        with Image(file=filep, resolution=96) as tiff:
            image_format = format.get('format')
            if image_format is not None:
                image = tiff.convert(image_format)
            else:
                image = tiff

            target_height = format.get('height')
            target_width = format.get('width')

            target_resolution = format.get('resolution')
            if target_resolution is not None:
                image.resolution = (target_resolution, target_resolution)

            if target_height is None and target_width is None:
                target_height = image.height
                target_width = image.width
            elif target_width is None:
                scale = float(target_height) / image.height
                target_width = int(image.width * scale)
            elif target_height is None:
                scale = float(target_width) / image.width
                target_height = int(image.height * scale)

            if target_height is not image.height or target_width is not image.width:
                image.resize(width=target_width, height=target_height)

            image_buffer = BytesIO()
            image.save(file=image_buffer)

    except Exception as e:
        message = "error resizing image %s" % info.filename
        logger.error(message, exc_info=True)
        raise RuntimeError("%s (%s)" % (message, e.message))

    filename = info.filename
    if format.get('prefix') is not None:
        filename = format.get('prefix') + filename
    if format.get('suffix') is not None:
        filename = filename + format.get('suffix')
    if format.get('extension') is not None:
        filename = filename + "." + format.get('extension')
    elif format.get('format') is not None:
        filename = filename + "." + format['format']
    else:
        filename += '.tiff'
    return filename, image_buffer
