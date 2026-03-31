#!/bin/bash
export DHAN_CLIENT_ID=1105513101
export DHAN_APP_ID=d475613b
export DHAN_APP_SECRET=89377389-e747-4387-bb50-f2cfa8c9d64c

cd /c/dhan-mcp
python monitor_nifty.py "$@"
