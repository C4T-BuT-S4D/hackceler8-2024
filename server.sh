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

extra_items=""
if [ -n "$EXTRA" ]; then
    extra_items="--extra-items $EXTRA"
fi

python3 server.py --hostname=localhost --port=8888 --ca="./ca/CA-devel.crt" --cert="./ca/dev-team.crt" --key="./ca/dev-team.key" $extra_items

cd $initialdir
