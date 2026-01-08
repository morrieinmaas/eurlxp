"""Test utilities for eurlxp."""


def merge_dicts(a: dict, b: dict, path: list | None = None) -> dict:
    """Recursively merge two dictionaries."""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass
            else:
                if a[key] is None:
                    a[key] = b[key]
                if b[key] is None:
                    b[key] = a[key]
        else:
            a[key] = b[key]
    return a


def convert_outline_item(outline_item: list) -> dict:
    """Convert an outline item to nested dict.

    Example: ["1", "a", "i."] -> {"1": {"a": {"i.": None}}}
    """
    if len(outline_item) == 1:
        return {outline_item[0]: None}
    node, remainder = outline_item[0], outline_item[1:]
    return {node: convert_outline_item(remainder)}


def convert_outline(outline_as_tuples: list[list]) -> dict:
    """Convert outline tuples to tree format.

    Example:
        [["1", "a", "i."], ["1", "a", "ii."], ["2"]]
        -> {"1": {"a": {"i.": None, "ii.": None}}, "2": None}
    """
    tree: dict = {}
    for item in outline_as_tuples:
        tree = merge_dicts(tree, convert_outline_item(item))
    return tree
