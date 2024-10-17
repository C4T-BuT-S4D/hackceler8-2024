from threading import RLock
from dataclasses import dataclass
from typing import Optional, Callable

from game.components.flags import Flags
from game.engine.generics import GenericObject

@dataclass
class MapObject:
    mapname: str
    obj: GenericObject

@dataclass
class MapFlag:
    mapname: str
    obj: GenericObject
    stars: int

@dataclass
class State:
    flags: list[MapFlag] = None
    coins: list[MapObject] = None

__lock: RLock = RLock()
__state: Optional[State] = None

def get_state() -> Optional[State]:
    with __lock:
        return __state

def update_state(upd: Callable[[State], None]):
    global __state
    with __lock:
        __state = upd(__state)
