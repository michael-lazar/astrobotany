#!/usr/bin/env bash
die () {
    echo >&2 "$@"
    exit 1
}
[ "$#" -eq 1 ] || die "Usage: generate_client_cert.sh [CLIENT_CN]"

mkdir -p certs/

openssl genrsa \
  -out certs/${1}.key 4096

openssl req \
  -new \
  -key certs/${1}.key \
  -out certs/${1}.req \
  -subj "/CN=${1}"

openssl x509 \
  -req \
  -in certs/${1}.req \
  -CA certs/ca.cer \
  -CAkey certs/ca.key \
  -set_serial 0x$(openssl rand -hex 16) \
  -extensions client \
  -days 3650 \
  -outform PEM \
  -out certs/${1}.cer
