from aws import s3
import re
import time

class BucketFileCheck:
    def __init__(self, s3, bucket_name, key):
        self._s3 = s3
        self._bucket_name = bucket_name
        self._key = key

    def of(self, **kwargs):
        criteria = self._key.format(**kwargs)
        i = 0
        while True: 
            bucket = self._s3.Bucket(self._bucket_name)
            bucket.load()
            for file in bucket.objects.all():
                print(file.key)
                if re.match(criteria, file.key):
                    return
            print "No match for %s yet..." % criteria
            i = i + 1
            if i > 12:
                raise RuntimeError("Timeout in polling for %s" % criteria)
            time.sleep(5)
        

eif = BucketFileCheck(s3, 'end2end-' + 'elife-publishing-eif', '{id}.1/.*/elife-{id}-v1.json')
