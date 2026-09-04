#!/bin/sh
# Dvojklik ve Finderu spustí aplikaci bez psaní příkazu do Terminálu.
# Musí ležet ve stejné složce jako naklikej_hrace.py.
cd "$(dirname "$0")" || exit 1
exec python3 naklikej_hrace.py
