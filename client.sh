#!/bin/bash
set -e

initialdir=$(pwd)
cd handout

if [ ! -d "env" ]; then
    python3 -m venv env
    source env/bin/activate
    pip install -r requirements.txt

    cd env/src/moderngl-window
    if [[ "$OSTYPE" == "darwin"* ]]; then
        patch -p1 < $initialdir/moderngl-window-retina.patch
    fi
    patch -p1 < $initialdir/moderngl-paste.patch
    cd $initialdir/handout
else
    source env/bin/activate
fi

if [ "$1" = "local" ]; then
  hostname="localhost"
  capath="./ca/CA-devel.crt"
  certpath="./ca/dev-team.crt"
  keypath="./ca/dev-team.key"
  standalone=""
elif [ "$1" = "remote" ]; then
  # TODO: change this to the actual hostname
  hostname="team6.hackceler8-2023.ctfcompetition.com"
  capath="$HOME/ca.crt"
  certpath="$HOME/team6"
  keypath="$HOME/team6.key"
  standalone=""
elif [ "$1" = "standalone" ]; then
  hostname=""
  certpath=""
  capath=""
  standalone="--standalone"
else
  echo "Specify local/remote/standalone as first argument"
  exit 1
fi

python3 client.py --hostname="$hostname" --port=8888 --ca="$capath" --cert="$certpath" --key="$keypath" $standalone

cd $initialdir
