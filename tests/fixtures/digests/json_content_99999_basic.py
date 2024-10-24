# coding=utf-8

from collections import OrderedDict

EXPECTED = OrderedDict(
    [
        ("id", "99999"),
        ("title", "Fishing for errors in the\xa0tests"),
        (
            "impactStatement",
            "Testing a document which mimics the format of a file we’ve used  before plus CO<sub>2</sub> and Ca<sup>2+</sup>.",
        ),
        (
            "image",
            OrderedDict(
                [
                    (
                        "thumbnail",
                        OrderedDict(
                            [
                                (
                                    "uri",
                                    "https://iiif.elifesciences.org/digests/99999%2Fdigest-99999.jpg",
                                ),
                                ("alt", ""),
                                (
                                    "source",
                                    OrderedDict(
                                        [
                                            ("mediaType", "image/jpeg"),
                                            (
                                                "uri",
                                                "https://iiif.elifesciences.org/digests/99999%2Fdigest-99999.jpg/full/full/0/default.jpg",
                                            ),
                                            ("filename", "digest-99999.jpg"),
                                        ]
                                    ),
                                ),
                                ("size", OrderedDict([("width", 1), ("height", 1)])),
                            ]
                        ),
                    ),
                ]
            ),
        ),
        (
            "content",
            [
                OrderedDict(
                    [
                        ("type", "image"),
                        (
                            "image",
                            OrderedDict(
                                [
                                    (
                                        "uri",
                                        "https://iiif.elifesciences.org/digests/99999%2Fdigest-99999.jpg",
                                    ),
                                    ("alt", ""),
                                    (
                                        "source",
                                        OrderedDict(
                                            [
                                                ("mediaType", "image/jpeg"),
                                                (
                                                    "uri",
                                                    "https://iiif.elifesciences.org/digests/99999%2Fdigest-99999.jpg/full/full/0/default.jpg",
                                                ),
                                                ("filename", "digest-99999.jpg"),
                                            ]
                                        ),
                                    ),
                                    (
                                        "size",
                                        OrderedDict([("width", 1), ("height", 1)]),
                                    ),
                                ]
                            ),
                        ),
                        (
                            "caption",
                            [
                                OrderedDict(
                                    [
                                        ("type", "paragraph"),
                                        (
                                            "text",
                                            "<b>It\u2019s not just mammals who can recognise sample data.</b>\u00a0Image credit:\u00a0Anonymous and Anonymous\u00a0(CC BY\u00a04.0)",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            "Being able to recognize sample data is crucial for social interactions in humans. This is also added, CO<sub>2</sub> or Ca<sup>2+</sup>, &amp; 1 &lt; 2. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            "Some other mammals also identify sample data. For example, female medaka fish (<i>Oryzias latipes</i>) prefer sample data they have seen before to ‘strangers’. However, until now, it was not known if they can recognize individual faces, nor how they distinguish a specific male from many others.",
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur, vel illum qui dolorem eum fugiat quo voluptas nulla pariatur?",
                        ),
                    ]
                ),
            ],
        ),
    ]
)
