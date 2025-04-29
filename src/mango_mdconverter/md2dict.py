from irods.meta import iRODSMeta
from mango_mdschema.helpers import flattened_from_mango_avu, unflatten


def safely_add_to_dict(regular_dict: dict, key, value, units=None):
    """Compile dictionary with key-value pairs or key-(value, units) pairs from AVUs.
    Make lists out of multivalued fields."""
    _value = value if units is None else (value, units)
    if key in regular_dict:
        if type(regular_dict[key]) == list:
            regular_dict[key].append(_value)
        elif type(regular_dict[key]) == dict and type(_value) != dict:
            safely_add_to_dict(regular_dict[key], "__value__", value, units)
        elif (existing_value := regular_dict[key]) is not None:
            regular_dict[key] = [existing_value, _value]
        else:  # basically None value
            regular_dict[key] = _value
    else:
        regular_dict[key] = _value


def unflatten_namespace_into_dict(
    target_dict: dict,
    namespaced_string: str,
    value=None,
    use_units=False,
    units=None,
) -> dict:
    """Expand namespaced string (with dots) into a nested dict

    Args:
        target_dict (dict): Dictionary to update: expanded AVU names
          will be keys, and values or tuples of values and units will
          be values.
        namespaced_string (str): AVU name
        value (str, optional): AVU value. Defaults to None.
        use_units (bool, optional): Whether units should be included. Defaults to False.
        units (str, optional): AVU units. Defaults to None.

    Returns:
        dict: Updated dictionary
    """
    if "." in namespaced_string:
        lead_key, rest = namespaced_string.split(".", 1)
        if lead_key not in target_dict:
            target_dict[lead_key] = {}
        if not isinstance(target_dict[lead_key], dict):
            target_dict[lead_key] = {"__value__": target_dict[lead_key]}
        unflatten_namespace_into_dict(
            target_dict[lead_key], rest, value, use_units, units
        )
    else:
        safely_add_to_dict(
            target_dict, namespaced_string, value, units if use_units else None
        )


def unpack_metadata_into_dict(target_dict: dict, avu: iRODSMeta) -> dict:
    """From a list of AVUs to a dictionary

    Example:
        metadict = {}
        for avu in obj.metadata.items():
            unpack_metadata_into_dict(metadict, avu)
    """
    unflatten_namespace_into_dict(target_dict, avu.name, avu.value, True, avu.units)


def prepare_metadata_for_download(metadict: dict, no_label: str = "other") -> dict:
    """Reorganize nested dictionary with schemas and analysis AVUs separated.
    To run on the output of `unpack_metadata_into_dict()`"""

    reorganized_metadata = {}
    for k, v in metadict.items():
        if type(v) == dict:
            if k == "schema":
                for schema_name, schema_avus in v.items():
                    v[schema_name] = unflatten(
                        list(
                            map(
                                lambda x: flattened_from_mango_avu(
                                    x, f"mgs.{schema_name}"
                                ),
                                schema_avus,
                            )
                        )
                    )
            reorganized_metadata[k] = v
        elif type(v) == tuple and v[1].startswith("analysis/"):
            if not "analysis" in reorganized_metadata:
                reorganized_metadata["analysis"] = {}
            analysis_subtype = v[1].replace("analysis/", "")
            if not analysis_subtype in reorganized_metadata["analysis"]:
                reorganized_metadata["analysis"][analysis_subtype] = {}
            reorganized_metadata["analysis"][analysis_subtype][k] = v[0]
        else:

            def remove_units(value):
                return value[0] if type(value) == tuple else value

            if not no_label in reorganized_metadata:
                reorganized_metadata[no_label] = {}
            reorganized_metadata[no_label][k] = (
                remove_units(v)
                if type(v) != list
                else [remove_units(value) for value in v]
            )
    return reorganized_metadata


def convert_metadata_to_dict(metadata_items) -> dict:
    """Convert iterable of iRODSMeta into nested dictionary

    Args:
        metadata_items (list of iRODSMeta): Metadata items from one data object or collection

    Example:
        convert_metadata_to_dict(irods_item.metadata.items())

    """
    metadict = {"schema": {}}
    for item in metadata_items:
        if item.name.startswith("mgs"):
            schema_name = item.name.split(".")[1]
            if schema_name not in metadict["schema"]:
                metadict["schema"][schema_name] = []
            if item.name.count(".") > 2 and item.units is None:
                item.units = ".".join(["1"] * (item.name.count(".") - 2))
            metadict["schema"][schema_name].append(item)
        else:
            unpack_metadata_into_dict(metadict, item)
    if len(metadict["schema"]) == 0:
        del metadict["schema"]
    return prepare_metadata_for_download(metadict)


def filter_metadata_dict(metadict, filters: dict = {}) -> dict:
    """Filter an dictionary of metadata to only retrieve certain keys.

    Args:
        metadict (any): Initially, the metadata dictionary, but then
          it is applied recursively to any value within the metadata dictionary.
        filters (dict or list, optional): An array or dictionary of keys, indicating which keys of
          the metadict should be included. For nested fields, the value should be
          another dict of the same format. Otherwise, an empty dictionary or
          `None` as value is enough. Defaults to `{}`, which results in the
          full dictionary being returned.

    Returns:
        dict: A (filtered) dictionary of metadata
    """
    # no filters = return everything
    if filters is None or len(filters) == 0:
        return metadict
    # allow array of keys
    if isinstance(filters, list):
        filters = {k: {} for k in filters}
    if not isinstance(filters, dict):
        raise TypeError(
            "The 'filters' argument should be a dictionary, an array of keys or empty."
        )
    # deal with repeatable composite fields
    if isinstance(metadict, list):
        return [filter_metadata_dict(d, filters) for d in metadict]

    if not isinstance(metadict, dict):
        raise TypeError("The metadata dictionary should be a dict or a list of dicts.")
    return {
        k: filter_metadata_dict(v, filters.get(k, {}))
        for k, v in metadict.items()
        if k in filters
    }
