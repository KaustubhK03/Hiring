from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Retrieve a value from a dictionary using a key in templates."""
    return dictionary.get(key, '')

@register.filter
def map_attribute(data_list, attribute):
    """Extracts a specific attribute from a list of dictionaries."""
    return [item.get(attribute, '') for item in data_list]