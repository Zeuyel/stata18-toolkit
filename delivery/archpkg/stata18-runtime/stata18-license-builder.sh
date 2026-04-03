#!/bin/sh
set -eu
exec python3 /opt/stata18-runtime/tools/stata18-license-builder.py "$@"
