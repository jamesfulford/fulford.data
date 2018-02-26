from checks import check
from data import Nexus
from data.accessors import *


entries = [
    {
        "id": 1,
        "optional_value": 3,
        "shallow": 5,
        "shallow_optional": "Hello, World!",
        "level1": {
            "deep_value": 7,
            "deep_matrix": [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ]
        },
        "sites": [
            {
                "s_id": 9,
                "s_has_icecream": 0,
            },
            {
                "s_id": 11
            }
        ],
        "matrix": [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ],
        "extra_data": {
            "key": 13,
            "key_optional": 15
        }
    },
    {
        "id": 2,
        "shallow": 4,
        "level1": {
            "deep_value": 6,
            "deep_value_optional": 8,
            "deep_matrix": [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ]
        },
        "sites": [
            {
                "s_id": 10,
                "deep_list_matrix": [
                    [10, 20, 30],
                    [40, 50, 60],
                    [70, 80, 90]
                ]

            },
            {
                "s_id": 12,
                "s_has_icecream": 1,
                "deep_list_matrix": [
                    [100, 200, 300],
                    [400, 500, 600],
                    [700, 800, 900]
                ]
            }
        ],
        "matrix": [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ],
        "extra_data": {
            "key": 14,
        }
    }

]


form = {
    "h_id": access("id"),  # single depth test
    "h_optional_value": access("optional_value", default=0),  # testing default

    "h_shallow": access(["shallow"]),  # single item dictionary path
    # single item path (optional)
    "h_shallow_optional": access(["shallow_optional"],
                                 default="default_value"),


    "h_deep": access(["level1", "deep_value"]),  # deep path, straight getter
    # deep path, straight getter (optional)
    "h_deep_optional": access(["level1", "deep_value_optional"], default=":)"),


    "h_site_ids": access(["sites", "s_id"]),  # access over a list
    # access over a list (optional)
    "h_site_icecreams": access(["sites", "s_has_icecream"],
                               default="no_icecream :("),

    # make sure list will return as list
    "h_access_list": access("matrix"),
    "h_access_flat_list": access("matrix", flatten=True),

    "h_try_extra_data": try_extra_data("key"),
    "h_try_extra_data_optional": try_extra_data("key_optional", default=0),

    "h_not_implemented": always("NOT IMPLEMENTED"),
    "h_blank": blank,

    # mapping will take default values, so no need to test with that
    "h_mapping_simple_f": access("id", mapping=lambda x: -x),
    "h_mapping_simple_d": access("id", mapping={1: 7}),

    "h_mapping_flat_list_f": access(["sites", "s_has_icecream"],
                                    default=0, mapping=bool),
    "h_mapping_flat_list_d": access(["sites", "s_has_icecream"],
                                    default=0, mapping={0: False, 1: True}),

    "h_mapping_stagger_list_f": access(["level1", "deep_matrix"],
                                       mapping=lambda x: x ** 2),
    "h_mapping_stagger_list_d": access(["level1", "deep_matrix"],
                                       mapping={5: 10}),
}

columns = {
    0: "h_id",
    1: "h_optional_value",
    2: "h_shallow",
    3: "h_shallow_optional",
    4: "h_deep",
    5: "h_deep_optional",
    6: "h_site_ids",
    7: "h_site_icecreams",
    8: "h_access_list",
    9: "h_access_flat_list",
    10: "h_try_extra_data",
    11: "h_try_extra_data_optional",
    12: "h_not_implemented",
    13: "h_blank",
    14: "h_mapping_simple_f",
    15: "h_mapping_simple_d",
    16: "h_mapping_flat_list_f",
    17: "h_mapping_flat_list_d",
    18: "h_mapping_stagger_list_f",
    19: "h_mapping_stagger_list_d",
}

expected = [
    [
        1, 3, 5, "Hello, World!", 7, ":)", [9, 11], [0, 'no_icecream :('],
        [[1, 2, 3], [4, 5, 6], [7, 8, 9]], [1, 2, 3, 4, 5, 6, 7, 8, 9],
        13, 15, "NOT IMPLEMENTED", "", -1, 7, [False, False],
        [False, False], [[1, 4, 9], [16, 25, 36], [49, 64, 81]],
        [[1, 2, 3], [4, 10, 6], [7, 8, 9]]
    ],
    [
        2, 0, 4, "default_value", 6, 8, [10, 12], ['no_icecream :(', 1],
        [[1, 2, 3], [4, 5, 6], [7, 8, 9]], [1, 2, 3, 4, 5, 6, 7, 8, 9],
        14, 0, "NOT IMPLEMENTED", "", -2, 2, [False, True],
        [False, True], [[1, 4, 9], [16, 25, 36], [49, 64, 81]],
        [[1, 2, 3], [4, 10, 6], [7, 8, 9]]
    ]
]


#
# Testing each column individually
#

def actual_and_expected(index):
    c = Nexus()
    my_form = {}
    my_form[columns[index - 1]] = form[columns[index - 1]]
    c.add(entries, my_form)
    return map(lambda e: e[columns[index - 1]], c.entries)


nexus_tests = map(lambda i: {"args": i, "expected": map(lambda e: e[i - 1],
                                                        expected)},
                  range(1, len(columns) + 1))


@check(nexus_tests)
def test_Nexus(index):
    return actual_and_expected(index)


@check(map(lambda e: {"expected": e}, expected))
def test_add_all_columns(*args):
    c = Nexus()
    c.add(entries, form)
    return c.entries
