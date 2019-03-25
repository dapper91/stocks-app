"""
Application custom json encoder.
"""

import enum
import flask


class CustomJSONEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return str(obj)

        return super().default(obj)
