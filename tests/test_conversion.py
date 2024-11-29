import unittest
from mango_mdconverter import md2dict
from irods.meta import iRODSMeta


class TestInIsolation(unittest.TestCase):
    def test_simple_unflattening(self):
        metadict = {}
        md2dict.unflatten_namespace_into_dict(metadict, "simple_name", "simple_value")
        self.assertEqual(metadict, {"simple_name": "simple_value"})

        md2dict.unflatten_namespace_into_dict(metadict, "simple_name", "simple_value2")
        self.assertEqual(metadict, {"simple_name": ["simple_value", "simple_value2"]})

        md2dict.unflatten_namespace_into_dict(
            metadict, "second_name", "second_value", use_units=True
        )
        self.assertEqual(
            metadict,
            {
                "simple_name": ["simple_value", "simple_value2"],
                "second_name": "second_value",
            },
        )

        md2dict.unflatten_namespace_into_dict(
            metadict, "third_name", "third_value", True, "units"
        )
        self.assertEqual(
            metadict,
            {
                "simple_name": ["simple_value", "simple_value2"],
                "second_name": "second_value",
                "third_name": ("third_value", "units"),
            },
        )

        md2dict.unflatten_namespace_into_dict(
            metadict, "third_name", "fourth_value", units="units"
        )
        self.assertEqual(
            metadict,
            {
                "simple_name": ["simple_value", "simple_value2"],
                "second_name": "second_value",
                "third_name": [("third_value", "units"), "fourth_value"],
            },
        )

    def test_namespaced_unflattening(self):
        metadict = {}
        md2dict.unflatten_namespace_into_dict(metadict, "level1.level2.level3", "value")
        self.assertEqual(metadict, {"level1": {"level2": {"level3": "value"}}})

        md2dict.unflatten_namespace_into_dict(
            metadict, "level1.level2", "value2", True, "units"
        )
        self.assertEqual(
            metadict, {"level1": {"level2": [{"level3": "value"}, ("value2", "units")]}}
        )


class TestMd2Dict(unittest.TestCase):
    def setUp(self):
        self.metadata_items = [
            iRODSMeta("mgs.book.author.name", "Fulano De Tal", "1"),
            iRODSMeta("mgs.book.author.age", "50", "1"),
            iRODSMeta("mgs.book.author.pet", "cat", "1"),
            iRODSMeta("mgs.book.author.name", "Jane Doe", "2"),
            iRODSMeta("mgs.book.author.age", "29", "2"),
            iRODSMeta("mgs.book.author.pet", "cat", "2"),
            iRODSMeta("mgs.book.author.pet", "parrot", "2"),
            iRODSMeta("mgs.book.title", "A random book title"),
            iRODSMeta("mg.mime_type", "text/plain"),
            iRODSMeta("page_n", "567", "analysis/reading"),
            iRODSMeta("chapter_n", "15", "analysis/reading"),
        ]

    def test_unpacking(self):
        metadict = {}
        md2dict.unpack_metadata_into_dict(metadict, self.metadata_items[0])
        self.assertEqual(
            metadict, {"mgs": {"book": {"author": {"name": ("Fulano De Tal", "1")}}}}
        )

        md2dict.unpack_metadata_into_dict(metadict, self.metadata_items[1])
        self.assertEqual(
            metadict,
            {
                "mgs": {
                    "book": {
                        "author": {"name": ("Fulano De Tal", "1"), "age": ("50", "1")}
                    }
                }
            },
        )

        md2dict.unpack_metadata_into_dict(
            metadict, iRODSMeta("chapter_n", "15", "analysis/reading")
        )
        self.assertEqual(
            metadict,
            {
                "mgs": {
                    "book": {
                        "author": {"name": ("Fulano De Tal", "1"), "age": ("50", "1")}
                    }
                },
                "chapter_n": ("15", "analysis/reading"),
            },
        )

    def test_mango_conversion(self):
        reorganized_dict = md2dict.convert_metadata_to_dict(self.metadata_items)
        expected_dict = {
            "schema": {
                "book": {
                    "author": [
                        {"age": "50", "name": "Fulano De Tal", "pet": "cat"},
                        {"age": "29", "name": "Jane Doe", "pet": ["cat", "parrot"]},
                    ],
                    "title": "A random book title",
                }
            },
            "mg": {"mime_type": "text/plain"},
            "analysis": {"reading": {"page_n": "567", "chapter_n": "15"}},
        }
        self.assertEqual(reorganized_dict, expected_dict)


if __name__ == "__main__":
    unittest.main()
