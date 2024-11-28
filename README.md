# Convert iRODS Metadata into a Python dictionary


The `md2dict` module of `mango_mdconverter` creates Python dictionaries
by flattening namespaced iRODS metadata items. This can be done:

- naively with regards to the semantics, simply unnesting the
  namespacing
  - also ignoring units
  - returning value-units tuples if units exist
- reorganizing the dictionary to bring ManGO schemas together and
  “analysis” metadata together

The module can be imported like so:

``` python
from mango_mdconverter import md2dict
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
