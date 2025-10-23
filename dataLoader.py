# ...existing code...
import json
import os
from typing import Any, Dict, Type, Optional, List, Protocol

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

    def save(self, path: str, objects: List[ToDictProto], ensure_dir: bool = True) -> None:
        if ensure_dir:
            dirpath = os.path.dirname(path)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)

        payload = []
        for obj in objects:
            payload.append({"type": obj.__class__.__name__, "data": obj.to_dict()})

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=self.indent)

    def load(self, path: str, ignore_unknown: bool = True) -> List[Any]:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        result: List[Any] = []
        for item in payload:
            typ = item.get("type")
            data = item.get("data", {})
            cls = self.type_map.get(typ)
            if cls:
                result.append(cls.from_dict(data))
            elif not ignore_unknown:
                raise ValueError(f"Unknown type: {typ!r}")
        return result
