from wand.image import Image

def resize(format, filep, info):
    try:
        with Image(file=filep) as img:
            print img.size[0]
            # TODO : resize and convert the image!
    except Exception as e:
        # TODO : log!
        print e

    return info.filename, filep
