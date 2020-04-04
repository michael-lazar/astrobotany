#!/usr/bin/env bash
mkdir -p certs/
openssl req \
  -nodes \
  -newkey rsa:4096 \
  -keyform PEM \
  -keyout certs/ca.key \
  -x509 \
  -days 3650 \
  -outform PEM \
  -out certs/ca.cer
