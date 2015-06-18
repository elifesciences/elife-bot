from wand.image import Image
import StringIO

def resize(format, filep, info):
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

            jp = StringIO.StringIO()
            image.save(file=jp)
    except Exception as e:
        # TODO : log!
        print e
    filename = info.full_filename
    filename = filename.replace(".tiff", "." + image_format)
    return filename, jp
