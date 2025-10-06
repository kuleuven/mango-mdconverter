# Convert iRODS Metadata into a Python dictionary


The `md2dict` module of `mango_mdconverter` creates Python dictionaries
by flattening namespaced iRODS metadata items. This can be done:

- naively with regards to the semantics, simply unnesting the
  namespacing
  - also ignoring units
  - returning value-units tuples if units exist
- reorganizing the dictionary to bring ManGO schemas together and
  “analysis” metadata together

You can install this package with `pip`:

``` python
pip install mango-mdconverter
```

    Requirement already satisfied: mango-mdconverter in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (0.0.8)
    Requirement already satisfied: mango-mdschema>=1.0.3 in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from mango-mdconverter) (1.0.3)
    Requirement already satisfied: python-irodsclient==2.2.0 in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from mango-mdconverter) (2.2.0)
    Requirement already satisfied: PrettyTable>=0.7.2 in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from python-irodsclient==2.2.0->mango-mdconverter) (3.12.0)
    Requirement already satisfied: defusedxml in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from python-irodsclient==2.2.0->mango-mdconverter) (0.7.1)
    Requirement already satisfied: six>=1.10.0 in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from python-irodsclient==2.2.0->mango-mdconverter) (1.16.0)
    Requirement already satisfied: validators>=0.22.0 in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from mango-mdschema>=1.0.3->mango-mdconverter) (0.22.0)
    Requirement already satisfied: wcwidth in /home/mariana/repos/github/kuleuven/mango-mdconverter/venv/lib/python3.12/site-packages (from PrettyTable>=0.7.2->python-irodsclient==2.2.0->mango-mdconverter) (0.2.13)

    [notice] A new release of pip is available: 24.3.1 -> 25.0
    [notice] To update, run: python -m pip install --upgrade pip
    Note: you may need to restart the kernel to use updated packages.

The module can be imported like so:

``` python
from mango_mdconverter import md2dict

# from mango_mdconverter.md2dict import convert_metadata_to_dict # to import a specific function
```

## Example

To understand this better, let’s look at some examples. We’ll simulate a
set of metadata from an iRODS item, and it looks like so:

``` python
from irods.meta import iRODSMeta

metadata_items = [
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
```

## Naive conversion

The `unflatten_namespace_into_dict()` function updates a dictionary with
the name-value pairs of an AVU, and optionally with the units as well.
Given a dictionary `metadict`, we can provide it an AVU name and value
to either add the respective keys and values to the dictionary or, if
the key already exists, to append the value to the list of values.

``` python
metadict = {}
md2dict.unflatten_namespace_into_dict(metadict, "AVU_name", "AVU_value")
metadict
```

    {'AVU_name': 'AVU_value'}

Metadata names with dots will be assumed to be namespaced: they will be
split and their values will become dictionaries themselves.

``` python
metadict = {}
md2dict.unflatten_namespace_into_dict(metadict, "level1.level2.level3", "AVU_value")
metadict
```

    {'level1': {'level2': {'level3': 'AVU_value'}}}

For a full list of metadata items, such as the output of the
`.metadata.items()` method of an iRODS data object or collection, we
could loop over the iterable:

``` python
metadict = {}
for avu in metadata_items:
    md2dict.unflatten_namespace_into_dict(metadict, avu.name, avu.value)
metadict
```

    {'mgs': {'book': {'author': {'name': ['Fulano De Tal', 'Jane Doe'],
        'age': ['50', '29'],
        'pet': ['cat', 'cat', 'parrot']},
       'title': 'A random book title'}},
     'mg': {'mime_type': 'text/plain'},
     'page_n': '567',
     'chapter_n': '15'}

As you can see from the example, the function can work ignoring units.
This functionality is sufficient for the opensearch indexing.

For ManGO schemas, however, we want to use the units to keep track of
repeatable composite fields. In order to achieve that, we just have to
also provide the unit and set the `use_units` argument to `True`.
<!-- TODO: Probably the argument is unnecessary? -->

The `unpack_metadata_to_dict()` is a wrapper around this function that
always uses units and takes the whole `irods.meta.iRODSMeta` object as
an argument instead of the name, value and units separately.

``` python
metadict = {}
for avu in metadata_items:
    md2dict.unpack_metadata_into_dict(metadict, avu)
metadict
```

    {'mgs': {'book': {'author': {'name': [('Fulano De Tal', '1'),
         ('Jane Doe', '2')],
        'age': [('50', '1'), ('29', '2')],
        'pet': [('cat', '1'), ('cat', '2'), ('parrot', '2')]},
       'title': 'A random book title'}},
     'mg': {'mime_type': 'text/plain'},
     'page_n': ('567', 'analysis/reading'),
     'chapter_n': ('15', 'analysis/reading')}

Now items with units are rendered as tuples of values and units, but
these are not interpreted in the context of ManGO. This is why this
approach is the “naïve” one: in order to reorganize this dictionary into
something that makes sense given how ManGO uses schemas and units, we
need to use another function.

## ManGO-specific conversion

The `convert_metadata_to_dict()` function takes an iterable of
`irods.meta.iRODSMeta` instances and returns a nested dictionary based
on the namespacing of the metadata names as well as the units. It works
upon the result of `unpack_metadata_into_dict()` and then reformats the
dictionary to group all metadata schemas under the “schemas” key
(instead of “mgs”) and to group all items with units starting with
“analysis/” under the “analysis” key. In addition, the repeatable
composite fields of schemas are reorganized properly based on their
units.

``` python
reorganized_dict = md2dict.convert_metadata_to_dict(metadata_items)
reorganized_dict
```

    {'schema': {'book': {'author': [{'age': '50',
         'name': 'Fulano De Tal',
         'pet': 'cat'},
        {'age': '29', 'name': 'Jane Doe', 'pet': ['cat', 'parrot']}],
       'title': 'A random book title'}},
     'mg': {'mime_type': 'text/plain'},
     'analysis': {'reading': {'page_n': '567', 'chapter_n': '15'}}}

This function is to be used when converting ManGO metadata into a
dictionary, in order to export it to a sidecar file, for downloading, or
in the context of cold storage.

## Dictionary filtering

The `filter_metadata_dict()` function allows you to filter the metadata
dictionary (naive or otherwise) based on the (nested) keys of interest.

Let’s say that from the naive metadata dictionary `metadict` we only
want the metadata fields from the “mgs” and “mg” namespaces - in that
case, the second argument is an array with the desired keys:

``` python
md2dict.filter_metadata_dict(metadict, ["mgs", "mg"])
```

    {'mgs': {'book': {'author': {'name': [('Fulano De Tal', '1'),
         ('Jane Doe', '2')],
        'age': [('50', '1'), ('29', '2')],
        'pet': [('cat', '1'), ('cat', '2'), ('parrot', '2')]},
       'title': 'A random book title'}},
     'mg': {'mime_type': 'text/plain'}}

We could do the same with the ManGO-specific organization, to for
example select the ManGO schemas and the analysis fields:

``` python
md2dict.filter_metadata_dict(reorganized_dict, ["schema", "analysis"])
```

    {'schema': {'book': {'author': [{'age': '50',
         'name': 'Fulano De Tal',
         'pet': 'cat'},
        {'age': '29', 'name': 'Jane Doe', 'pet': ['cat', 'parrot']}],
       'title': 'A random book title'}},
     'analysis': {'reading': {'page_n': '567', 'chapter_n': '15'}}}

This level of filtering is equivalent to doing the following:

``` python
{k: v for k, v in reorganized_dict.items() if k in ["schema", "analysis"]}
```

    {'schema': {'book': {'author': [{'age': '50',
         'name': 'Fulano De Tal',
         'pet': 'cat'},
        {'age': '29', 'name': 'Jane Doe', 'pet': ['cat', 'parrot']}],
       'title': 'A random book title'}},
     'analysis': {'reading': {'page_n': '567', 'chapter_n': '15'}}}

Where this function comes in particularly handy is when you want to
filter nested fields. Say, for example, that you want to only retrieve
specific schemas and/or specific analysis fields. While our example has
only one schema, we can illustrate by selecting only the “title” of the
“book” schema, discarding the “author”:

``` python
md2dict.filter_metadata_dict(reorganized_dict, {"schema": {"book": ["title"]}})
```

    {'schema': {'book': {'title': 'A random book title'}}}

We can combine these partial dictionaries with full dictionaries
(e.g. all of “analysis”) by providing an empty dictionary when we don’t
want to filter further:

``` python
md2dict.filter_metadata_dict(
    reorganized_dict, {"schema": {"book": ["title"]}, "analysis": {}}
)
```

    {'schema': {'book': {'title': 'A random book title'}},
     'analysis': {'reading': {'page_n': '567', 'chapter_n': '15'}}}

This also works with repeatable composite fields. For example, by
selecting only the “pet” and “name” of the “author” composite field,
we’ll get an array of dictionaries with only the “pet” and “name” keys:

``` python
md2dict.filter_metadata_dict(
    reorganized_dict, {"schema": {"book": {"author": ["name", "pet"]}}}
)
```

    {'schema': {'book': {'author': [{'name': 'Fulano De Tal', 'pet': 'cat'},
        {'name': 'Jane Doe', 'pet': ['cat', 'parrot']}]}}}
