import sys
import re
import requests
from provider.utils import pad_msid, unicode_encode


"""
glencoe_resp = {
    "media1": {
        "source_href": "https://static-movie-usa.glencoesoftware.com/source/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.wmv",
        "doi": "10.7554/eLife.00569.019",
        "flv_href": "https://static-movie-usa.glencoesoftware.com/flv/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.flv",
        "uuid": "55f163d5-f0d9-415b-8ae8-ec75ed83b026",
        "title": "",
        "video_id": "media1",
        "solo_href": "https://movie-usa.glencoesoftware.com/video/10.7554/eLife.00569/media1",
        "height": 480,
        "ogv_href": "https://static-movie-usa.glencoesoftware.com/ogv/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.ogv",
        "width": 640,
        "href": "elife-00569-media1.wmv",
        "webm_href": "https://static-movie-usa.glencoesoftware.com/webm/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.webm",
        "jpg_href": "https://static-movie-usa.glencoesoftware.com/jpg/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.jpg",
        "duration": 54.487,
        "mp4_href": "https://static-movie-usa.glencoesoftware.com/mp4/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.mp4",
        "legend": "",
        "size": 20452423
    }
}
"""


def validate_sources(gc_data):

    sources = {
        "mp4": 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"',
        "webm": 'video/webm; codecs="vp8.0, vorbis"',
        "ogv": 'video/ogg; codecs="theora, vorbis"',
    }
    known_sources = list(sources.keys())

    for v_id, v_data in list(gc_data.items()):
        # we can't guarantee all of the sources will always be present
        available_sources = [
            mtype for mtype in known_sources if mtype + "_href" in v_data
        ]

        # fail if we have partial data
        msg = (
            "number of available sources (%r) less than known sources for %r. missing: %s"
            % (
                len(available_sources),
                v_id,
                ", ".join(set(known_sources) - set(available_sources)),
            )
        )
        assert len(available_sources) == len(known_sources), msg


def metadata(msid, settings):
    doi = "10.7554/eLife." + pad_msid(msid)
    url = settings.video_url + doi

    resp = requests.get(url)

    assert resp.status_code != 404, "article has no videos - url requested: %s" % url
    assert (
        resp.status_code == 200
    ), "unhandled status code from Glencoe: %s - url requested: %s" % (
        resp.status_code,
        url,
    )

    return resp.json()


def jpg_href_values(video_metadata):
    return [val["jpg_href"] for val in video_metadata.values() if "jpg_href" in val]


def has_videos(xml_str):
    if re.search(r'<media[^>]*mimetype="video".*?>', unicode_encode(xml_str)):
        return True
    return False


def check_msid(msid):
    """Replaces the msid of testing articles with the reference one they were generated from.
    Leaves real articles AND the kitchen sink untouched.

    Testing uses actual articles and generate a very long random msid from their shorter one.
      for example: 09560 => 5432109560 (trailing msid is preserved)

    All instances of the msid in the XML are replaced with this generated msid.
    `check_msid` *truncates* this so external references continue pointing to the actual article assets.
      for example: 5432109560 => 09560

    The kitchen sink however is its own article with its own set of videos.
    Its msid is still changed from 1234567890 to a generated one during testing *except* for video hrefs.
    See `elife-spectrum/update-kitchen-sinks-from-github.sh`."""
    msid = int(msid)
    kitchen_sink_id = 1234567890
    # check if rightmost digits match the kitchen_sink_id
    if int(str(msid)[-10:]) == kitchen_sink_id:
        return str(msid)[-10:]
    if msid > 1000000:  # 1M, previously 100k
        return pad_msid(str(msid)[-5:])
    return pad_msid(msid)


def force_article_id(filename, article_id):
    "In case of testing, we have generated article ids pointing to real article ids on Glencoe. This function forces the generated article id on a file coming from outside."
    padded_article_id = check_msid(article_id)
    if padded_article_id == article_id:
        return filename
    return filename.replace(padded_article_id, article_id)


def main(msid):
    try:
        validate_sources(metadata(msid))
        return True
    except AssertionError as err:
        return False


if __name__ == "__main__":
    sys.exit(0) if main(sys.argv[1]) else sys.exit(1)
