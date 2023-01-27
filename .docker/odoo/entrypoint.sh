#!/usr/bin/env bash

set -e

if [[ "$1" == "runbot" ]] ; then
  shift
  wait-for-sql
  exec ~/instance/odoo/odoo-bin -i runbot_travis2docker --without-demo=all "$@"
else
  exec "$@"
fi
