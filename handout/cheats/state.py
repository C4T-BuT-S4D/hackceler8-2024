from threading import RLock
from game.components.flags import Flags
from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class State:
    flags: Flags = None

__lock: RLock = RLock()
__state: Optional[State] = None

def get_state() -> Optional[State]:
    with __lock:
        return __state

def update_state(upd: Callable[[State], None]):
    global __state
    with __lock:
        __state = upd(__state)
