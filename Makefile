PROTOC ?= protoc
PYTHON ?= python3

.PHONY: check

check:
	$(PYTHON) tests/check_contract.py --protoc $(PROTOC) proto/zmk/runtime_config.proto
