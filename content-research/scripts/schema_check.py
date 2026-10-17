"""A tiny JSON Schema subset validator, so the scripts need no dependencies.

Supports: type (string or list), enum, required, properties, additionalProperties
(bool or schema), items, minLength, pattern, minimum, maximum. Anything else in a
schema is ignored, so keep schemas in this repo within that subset.
"""
from __future__ import annotations

import json
import os
import re

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas")


def load_schema(name):
    with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _is_type(value, name):
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "null":
        return value is None
    raise ValueError(f"unsupported type in schema: {name}")


def validate(instance, schema, path="$"):
    """Return a list of error strings; empty means valid."""
    types = schema.get("type")
    if types is not None:
        names = types if isinstance(types, list) else [types]
        if not any(_is_type(instance, n) for n in names):
            return [f"{path}: expected {' or '.join(names)}, got {type(instance).__name__}"]

    errors = []
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: is empty or too short")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} is below {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} is above {schema['maximum']}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field {key!r}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unexpected field {key!r}")
            elif isinstance(extra, dict):
                errors += validate(value, extra, f"{path}.{key}")

    if isinstance(instance, list) and "items" in schema:
        for i, value in enumerate(instance):
            errors += validate(value, schema["items"], f"{path}[{i}]")

    return errors
