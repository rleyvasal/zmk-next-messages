#!/usr/bin/env python3
"""Compile the Runtime Config schema and guard its v0.1 wire field numbers."""

import argparse
import pathlib
import subprocess
import tempfile

from google.protobuf import descriptor_pb2


EXPECTED_FIELDS = {
    "zmk.studio.Request": {
        "request_id": 1,
        "core": 3,
        "behaviors": 4,
        "keymap": 5,
        "runtime_config": 6,
    },
    "zmk.studio.RequestResponse": {
        "request_id": 1,
        "meta": 2,
        "core": 3,
        "behaviors": 4,
        "keymap": 5,
        "runtime_config": 6,
    },
    "zmk.runtime_config.Request": {
        "request_id": 1,
        "get_runtime_capabilities": 2,
        "get_runtime_config_status": 3,
        "get_runtime_config": 4,
        "begin_runtime_update": 5,
        "upload_runtime_update_chunk": 6,
        "validate_runtime_update": 7,
        "commit_runtime_update": 8,
        "abort_runtime_update": 9,
        "reset_runtime_config": 10,
    },
    "zmk.runtime_config.Response": {
        "request_id": 1,
        "error": 2,
        "get_runtime_capabilities": 3,
        "get_runtime_config_status": 4,
        "get_runtime_config": 5,
        "begin_runtime_update": 6,
        "upload_runtime_update_chunk": 7,
        "validate_runtime_update": 8,
        "commit_runtime_update": 9,
        "abort_runtime_update": 10,
        "reset_runtime_config": 11,
    },
    "zmk.runtime_config.RuntimeConfigSnapshot": {
        "persistence_schema_version": 1,
        "generation": 2,
        "capability_fingerprint": 3,
        "keymap_overrides": 4,
        "layers": 5,
        "runtime_objects": 6,
        "combos": 7,
    },
    "zmk.runtime_config.ActionReference": {
        "compiled_behavior": 1,
        "runtime_object_id": 2,
    },
    "zmk.runtime_config.RuntimeObject": {
        "id": 1,
        "mod_morph": 2,
        "macro": 3,
        "hold_tap": 4,
        "tap_dance": 5,
    },
    "zmk.runtime_config.RuntimeConfigLimits": {
        "max_runtime_objects": 1,
        "max_combos": 2,
        "max_combo_keys": 3,
        "max_macro_steps": 4,
        "max_persisted_bytes": 5,
        "max_layers": 6,
        "max_keymap_overrides": 7,
        "max_tap_dance_actions": 8,
    },
    "zmk.runtime_config.ComboDefinition": {
        "id": 1,
        "key_positions": 2,
        "timeout_ms": 3,
        "output": 4,
        "slow_release": 5,
        "require_prior_idle_ms": 6,
    },
    "zmk.runtime_config.RuntimeConfigDiagnostic": {
        "severity": 1,
        "code": 2,
        "message": 3,
        "runtime_object_id": 4,
        "combo_id": 5,
        "key_location": 6,
        "field_path": 7,
    },
    "zmk.runtime_config.RuntimeConfigResourceUsage": {
        "runtime_objects": 1,
        "combos": 2,
        "macro_steps": 3,
        "persisted_bytes": 4,
        "keymap_overrides": 5,
        "tap_dance_actions": 6,
    },
}


def iter_messages(package, messages):
    for message in messages:
        qualified_name = f"{package}.{message.name}"
        yield qualified_name, message
        yield from iter_messages(qualified_name, message.nested_type)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protoc", required=True)
    parser.add_argument("proto", type=pathlib.Path)
    args = parser.parse_args()

    proto = args.proto.resolve()
    with tempfile.TemporaryDirectory() as temp_dir:
        descriptor_path = pathlib.Path(temp_dir) / "runtime_config.pb"
        subprocess.run(
            [
                args.protoc,
                f"--proto_path={proto.parent}",
                f"--descriptor_set_out={descriptor_path}",
                "--include_imports",
                str(proto),
            ],
            check=True,
        )

        descriptor_set = descriptor_pb2.FileDescriptorSet()
        descriptor_set.ParseFromString(descriptor_path.read_bytes())

    messages = {
        name: message
        for file_descriptor in descriptor_set.file
        for name, message in iter_messages(file_descriptor.package, file_descriptor.message_type)
    }

    for message_name, expected_fields in EXPECTED_FIELDS.items():
        if message_name not in messages:
            raise AssertionError(f"missing message: {message_name}")

        actual_fields = {field.name: field.number for field in messages[message_name].field}
        for field_name, field_number in expected_fields.items():
            actual_number = actual_fields.get(field_name)
            if actual_number != field_number:
                raise AssertionError(
                    f"{message_name}.{field_name}: expected tag {field_number}, got {actual_number}"
                )

    print("runtime-config v0.1 contract check passed")


if __name__ == "__main__":
    main()
