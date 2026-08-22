#!/usr/bin/env python3
"""Generate JS field/enum-number constants from the Runtime Config protobuf schema.

Mirrors check_contract.py's protoc introspection so the browser-side
configurator never has to hand-copy a wire field or enum number again.
Output is deterministic (no timestamp, no protoc version) so it can be
diffed for staleness by zmk-next-configurator/scripts/sync-messages.sh.
"""

import argparse
import json
import pathlib
import subprocess
import tempfile

from google.protobuf import descriptor_pb2


def iter_messages(messages):
    for message in messages:
        yield message.name, message
        for nested_name, nested in iter_messages(message.nested_type):
            yield f"{message.name}.{nested_name}", nested


def iter_enums(enums, messages):
    for enum in enums:
        yield enum.name, enum
    for message in messages:
        for nested_name, nested in iter_enums(message.enum_type, message.nested_type):
            yield f"{message.name}.{nested_name}", nested


def set_path(tree, dotted_name, leaf_value):
    parts = dotted_name.split(".")
    node = tree
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    if parts[-1] in node:
        raise AssertionError(f"duplicate key while building tree: {dotted_name}")
    node[parts[-1]] = leaf_value


def js_object(value, indent=0):
    if not isinstance(value, dict):
        return json.dumps(value)
    if not value:
        return "Object.freeze({})"
    pad = "  " * indent
    inner_pad = "  " * (indent + 1)
    lines = [
        f"{inner_pad}{json.dumps(key)}: {js_object(val, indent + 1)},"
        for key, val in value.items()
    ]
    return "Object.freeze({\n" + "\n".join(lines) + f"\n{pad}}})"


def compile_descriptor_set(protoc, proto):
    with tempfile.TemporaryDirectory() as temp_dir:
        descriptor_path = pathlib.Path(temp_dir) / "messages.pb"
        subprocess.run(
            [
                protoc,
                f"--proto_path={proto.parent}",
                f"--descriptor_set_out={descriptor_path}",
                "--include_imports",
                str(proto),
            ],
            check=True,
        )
        descriptor_set = descriptor_pb2.FileDescriptorSet()
        descriptor_set.ParseFromString(descriptor_path.read_bytes())
        return descriptor_set


def build_trees(descriptor_set):
    fields_tree = {}
    enums_tree = {}
    for file_descriptor in descriptor_set.file:
        package = file_descriptor.package
        leaf = package.split(".")[-1] if package else file_descriptor.name
        for name, message in iter_messages(file_descriptor.message_type):
            field_map = {field.name: field.number for field in message.field}
            set_path(fields_tree.setdefault(leaf, {}), name, field_map)
        for name, enum in iter_enums(file_descriptor.enum_type, file_descriptor.message_type):
            value_map = {value.name: value.number for value in enum.value}
            set_path(enums_tree.setdefault(leaf, {}), name, value_map)
    return fields_tree, enums_tree


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protoc", required=True)
    parser.add_argument(
        "--sha", default=None, help="zmk-next-messages commit the .proto was read from"
    )
    parser.add_argument("proto", type=pathlib.Path)
    args = parser.parse_args()

    descriptor_set = compile_descriptor_set(args.protoc, args.proto.resolve())
    fields_tree, enums_tree = build_trees(descriptor_set)

    header = [
        "// GENERATED FILE -- do not edit by hand.",
        "// Produced by zmk-next-messages/tools/gen_js_fields.py from proto/zmk/*.proto.",
        "// Regenerate with zmk-next-configurator/scripts/sync-messages.sh.",
    ]
    if args.sha:
        header.append(f"// Source: zmk-next-messages @ {args.sha}")

    print("\n".join(header))
    print()
    print(f"export const FIELDS = {js_object(fields_tree)};")
    print()
    print(f"export const ENUMS = {js_object(enums_tree)};")


if __name__ == "__main__":
    main()
