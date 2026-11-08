#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "03008c79030404935463ef8d11fc56518738f2eb055e69f931827dfff9224b65  source.tar.xz" > archive.sha256
base64 -d source.tar.xz.base64 > source.tar.xz
sha256sum -c archive.sha256
tar -xJf source.tar.xz
test -f dect-ra/RandomAccessModel.cc
test -f dect-ra/DectRandomAccess.ned
test -f dect-ra/omnetpp.ini
test -f dect-ra/.project
echo "Restored original ZIP contents:"
find dect-ra -type f | sort
rm source.tar.xz
