from dataclasses import dataclass

@dataclass
class TickData:
    keys: list[str]
    text_input: str | None = None
    force_keys: bool = False
