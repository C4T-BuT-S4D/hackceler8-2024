from dataclasses import dataclass


@dataclass
class Macro:
    name: str
    keys: str
    force_keys: bool = False
