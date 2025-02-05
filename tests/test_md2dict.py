import pytest
from mango_mdconverter import md2dict
from irods.meta import iRODSMeta


def test_simple_unflattening():
    metadict = {}
    md2dict.unflatten_namespace_into_dict(metadict, "simple_name", "simple_value")
    assert metadict == {"simple_name": "simple_value"}

    md2dict.unflatten_namespace_into_dict(metadict, "simple_name", "simple_value2")
    assert metadict == {"simple_name": ["simple_value", "simple_value2"]}

    md2dict.unflatten_namespace_into_dict(
        metadict, "second_name", "second_value", use_units=True
    )
    assert metadict == {
        "simple_name": ["simple_value", "simple_value2"],
        "second_name": "second_value",
    }

    md2dict.unflatten_namespace_into_dict(
        metadict, "third_name", "third_value", True, "units"
    )
    assert metadict == {
        "simple_name": ["simple_value", "simple_value2"],
        "second_name": "second_value",
        "third_name": ("third_value", "units"),
    }

    md2dict.unflatten_namespace_into_dict(
        metadict, "third_name", "fourth_value", units="units"
    )
    assert metadict == {
        "simple_name": ["simple_value", "simple_value2"],
        "second_name": "second_value",
        "third_name": [("third_value", "units"), "fourth_value"],
    }


def test_namespaced_unflattening():
    metadict = {}
    md2dict.unflatten_namespace_into_dict(metadict, "level1.level2.level3", "value")
    assert metadict == {"level1": {"level2": {"level3": "value"}}}

    md2dict.unflatten_namespace_into_dict(
        metadict, "level1.level2", "value2", True, "units"
    )
    assert metadict == {
        "level1": {"level2": {"level3": "value", "__value__": ("value2", "units")}}
    }


@pytest.fixture
def metadata_items():
    return [
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


@pytest.fixture
def bad_namespacing():
    return [
        iRODSMeta("ns.section", "1"),
        iRODSMeta("ns.section.title", "section_title"),
    ]


@pytest.fixture
def bad_namespacing_converted():
    return {"ns": {"section": {"title": "section_title", "__value__": "1"}}}


@pytest.fixture
def converted_dict():
    return {
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


def test_unpacking(metadata_items):
    metadict = {}
    md2dict.unpack_metadata_into_dict(metadict, metadata_items[0])
    assert metadict == {"mgs": {"book": {"author": {"name": ("Fulano De Tal", "1")}}}}

    md2dict.unpack_metadata_into_dict(metadict, metadata_items[1])
    assert metadict == {
        "mgs": {
            "book": {"author": {"name": ("Fulano De Tal", "1"), "age": ("50", "1")}}
        }
    }

    md2dict.unpack_metadata_into_dict(
        metadict, iRODSMeta("chapter_n", "15", "analysis/reading")
    )
    assert metadict == {
        "mgs": {
            "book": {"author": {"name": ("Fulano De Tal", "1"), "age": ("50", "1")}}
        },
        "chapter_n": ("15", "analysis/reading"),
    }


def test_mango_conversion(metadata_items, converted_dict):
    reorganized_dict = md2dict.convert_metadata_to_dict(metadata_items)
    assert reorganized_dict == converted_dict

    # metadata_items.reverse()
    # reorganized_dict2 = md2dict.convert_metadata_to_dict(metadata_items)
    # assert reorganized_dict2 == converted_dict


def test_bad_namespacing_conversion(bad_namespacing, bad_namespacing_converted):
    reorganized_dict = md2dict.convert_metadata_to_dict(bad_namespacing)
    assert reorganized_dict == bad_namespacing_converted

    bad_namespacing.reverse()
    reorganized_dict = md2dict.convert_metadata_to_dict(bad_namespacing)
    assert reorganized_dict == bad_namespacing_converted
