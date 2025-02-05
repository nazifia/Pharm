# converters.py

import shortuuid

class ShortUUIDConverter:
    regex = 'RID:[A-Za-z0-9]{5}'  # Adjust the regex based on your ShortUUID configuration (length, alphabet)

    def to_python(self, value):
        return value

    def to_url(self, value):
        return str(value)
