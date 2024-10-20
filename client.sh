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

pushd ../cheats-rust/search
if [ ! -d "../target" ]; then
    maturin build --profile opt -i $(which python3)
    pip install --force-reinstall ../target/wheels/*
fi
popd

if [ "$1" = "local" ]; then
  hostname="localhost"
  capath="./ca/CA-devel.crt"
  certpath="./ca/dev-team.crt"
  keypath="./ca/dev-team.key"
  standalone=""
elif [ "$1" = "remote" ]; then
  hostname="team6.hackceler8-2024.ctfcompetition.com"
  capath="$HOME/team6/ca.crt"
  certpath="$HOME/team6/server.crt"
  keypath="$HOME/team6/server.key"
  standalone=""
elif [ "$1" = "standalone" ]; then
  hostname=""
  certpath=""
  capath=""
  standalone="--standalone"
elif [ "$1" = "prerender" ]; then
  hostname=""
  certpath=""
  capath=""
  standalone="--standalone --prerender"
else
  echo "Specify local/remote/standalone/prerender as first argument"
  exit 1
fi

extra_items=""
if [ -n "$EXTRA" ]; then
    extra_items="--extra-items $EXTRA"
fi


python3 client.py --hostname="$hostname" --port=8888 --ca="$capath" --cert="$certpath" --key="$keypath" $standalone $extra_items

cd $initialdir
