## Directory structure

- `handout/` - complete game handout initially copied from the google-ctf repo, this should contain unpatched source code of current game version on branch `unpatched` and the current game version patched with cheats on `master`
- `handout/env` - initialized by `client.sh`/`server.sh` with python venv
setup, `moderngl-window-retina.patch` is applied to `env/src/moderngl-window` to include the MacOS GUI rendering fix. If rollback is required, just `cd handout/env/src/moderngl-window && git restore .`

## Commands
- `./client.sh standalone` for basic testing, screenshotting, etc
- `./server.sh` and `./client.sh local` for proper local testing with serverside cheat detection
- `./client.sh remote` to actually play the game
