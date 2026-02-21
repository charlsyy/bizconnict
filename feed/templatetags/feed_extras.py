from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    if d is None:
        return None
    try:
        return d.get(key)
    except Exception:
        try:
            return d[key]
        except Exception:
            return None

@register.filter
def reaction_count(summary, key):
    """
    summary can be:
    - dict like {'like': 2, 'heart': 1}
    - list like [{'reaction_type':'like','count':2}, ...]
    - list of tuples like [('like',2), ...]
    Returns count for the reaction key, else 0.
    """
    if not summary:
        return 0

    # dict
    if isinstance(summary, dict):
        try:
            return summary.get(key, 0)
        except Exception:
            return 0

    # list forms
    try:
        for item in summary:
            if isinstance(item, dict):
                if item.get('reaction_type') == key:
                    return item.get('count', 0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                if item[0] == key:
                    return item[1]
    except Exception:
        return 0

    return 0