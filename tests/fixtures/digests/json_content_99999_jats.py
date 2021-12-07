# coding=utf-8

from collections import OrderedDict

EXPECTED = OrderedDict(
    [
        ("id", u"99999"),
        ("title", u"Fishing for errors in the\xa0tests"),
        (
            "impactStatement",
            u"Testing a document which mimics the format of a file we’ve used  before plus CO<sub>2</sub> and Ca<sup>2+</sup>.",
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
            "subjects",
            [
                OrderedDict(
                    [
                        ("id", "ecology"),
                        ("name", "Ecology"),
                    ]
                ),
                OrderedDict(
                    [
                        ("id", "computational-systems-biology"),
                        ("name", "Computational and Systems Biology"),
                    ]
                ),
            ],
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
                                            u"<b>It\u2019s not just mammals who can recognise sample data.</b>\u00a0Image credit:\u00a0Anonymous and Anonymous\u00a0(CC BY\u00a04.0)",
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
                            u'Microbes live in us and on us. They are tremendously important for our health, but remain difficult to understand, since a microbial community typically consists of hundreds of species that interact in complex ways that we cannot fully characterize. It is tempting to ask whether one might instead characterize such a community as a whole, treating it as a multicellular "super-organism". However, taking this view beyond a metaphor is controversial, because the formal criteria of multicellularity require pervasive levels of cooperation between organisms that do not occur in most natural communities.',
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            u'In nature, entire communities of microbes routinely come into contact \u2013 for example, kissing can mix together the communities in each person\u2019s mouth. Can such events be usefully described as interactions between community-level "wholes", even when individual bacteria do not cooperate with each other? And can these questions be asked in a rigorous mathematical framework?',
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            u'Mikhail Tikhonov has now developed a theoretical model that shows that communities of purely "selfish" members may effectively act together when competing with another community for resources. This model offers a new way to formalize the "super-organism" metaphor: although individual members compete against each other within a community, when seen from the outside the community interacts with its environment and with other communities much like a single organism.',
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            u"This perspective blurs the distinction between two fundamental concepts: competition and genetic recombination. Competition combines two communities to produce a third where species are grouped in a new way, just as the genetic material of parents is recombined in their offspring.",
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        ("type", "paragraph"),
                        (
                            "text",
                            u"Tikhonov\u2019s model is highly simplified, but this suggests that the \"cohesion\" seen when viewing an entire community is a general consequence of ecological interactions. In addition, the model considers only competitive interactions, but in real life, species depend on each other; for example, one organism's waste is another's food. A natural next step would be to incorporate such cooperative interactions into a similar model, as cooperation is likely to make community cohesion even stronger.",
                        ),
                    ]
                ),
            ],
        ),
    ]
)
