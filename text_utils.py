
from dataclasses import dataclass


@dataclass
class TextEntry:
    text: str
    text_uuid: str
    line_id: str

@dataclass(frozen=True)
class TextKey:
    dialog_node_id: str
    line_id: str
