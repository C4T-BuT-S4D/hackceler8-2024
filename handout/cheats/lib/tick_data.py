from dataclasses import dataclass
from game.engine.keys import Keys

@dataclass
class TickData:
    keys: list[Keys]
    text_input: str | None = None
    force_keys: bool = False
