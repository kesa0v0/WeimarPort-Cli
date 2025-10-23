# ...existing code...
import json
import os
from typing import Any, Dict, Type, Optional, List, Protocol
import config

from datas import PartyData, CityData, UnitData

class ToDictProto(Protocol):
    def to_dict(self) -> Dict[str, Any]:
        ...

DEFAULT_TYPE_MAP: Dict[str, Type[Any]] = {
    "PartyData": PartyData,
    "CityData": CityData,
    "UnitData": UnitData,
}

class DataLoader:
    def __init__(self, type_map: Optional[Dict[str, Type[Any]]] = None, *, indent: int = 2):
        self.type_map = dict(DEFAULT_TYPE_MAP)
        if type_map:
            self.type_map.update(type_map)
        self.indent = indent

    def load(self, path: str, ignore_unknown: bool = True) -> List[Any]:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        result: List[Any] = []
        for item in payload:
            typ = item.get("type")
            data = item.get("data", {})
            cls = self.type_map.get(typ)
            if cls:
                obj = cls.from_dict(data)
                result.append(obj)
                if config.DEBUG:  # Log each loaded object if DEBUG is True
                    print(f"[DEBUG] Loaded object: {obj}")
            elif not ignore_unknown:
                raise ValueError(f"Unknown type: {typ!r}")
        return result
