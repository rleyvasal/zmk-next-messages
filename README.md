# ZMK Next Messages

This repository owns the public protobuf contract between a ZMK Next firmware
build and ZMK Next Configurator. It intentionally does not contain firmware
persistence layouts, generated source, or editor state.

## Version 0.1.0

`proto/zmk/runtime_config.proto` defines the Runtime Config v1 subsystem:

- capability, status, and active-snapshot reads;
- transactional full-snapshot uploads in chunks;
- validation, commit, abort, and reset operations; and
- typed models for actions, runtime objects, macros, combos, hold-taps,
  mod-morphs, and tap-dances.

The on-device persistent format remains private to firmware. A client uploads
a protobuf `RuntimeConfigSnapshot`; firmware validates it, serializes it to its
own format, and returns a firmware-assigned generation.

`protocol_version` describes compatibility of this RPC contract.
`persistence_schema_version` describes a firmware's private snapshot storage.
`capability_fingerprint` identifies the engines and fixed resource limits in a
specific firmware build.

Both `zmk-next` and `zmk-next-configurator` must pin the same tagged release or
commit of this repository.

## Compatibility rules

- Never reuse or renumber a protobuf field number.
- Add new fields and enum values only; preserve existing wire meanings.
- Keep a complete snapshot as the only write model in v0.1.
- Use nonzero request IDs. A response always echoes its request ID.
- Treat `RuntimeConfigError` and `ValidationResult` as the authoritative
  machine-readable status; text is for display only.

Run the following to compile the descriptor and verify the protected v0.1 field
numbers:

```sh
python3 -m pip install -r requirements-dev.txt
make check
```
