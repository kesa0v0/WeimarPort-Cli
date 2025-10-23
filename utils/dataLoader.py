import json
import logging
from typing import Any, Dict, Type, Optional, List, Protocol

from datas import PartyData, CityData, UnitData


logger = logging.getLogger(__name__)

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
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            raise

        result: List[Any] = []
        for item in payload:
            typ = item.get("type")
            data = item.get("data", {})
            cls = self.type_map.get(typ)
            if cls:
                try:
                    obj = cls.from_dict(data)
                    result.append(obj)
                    logger.debug(f"Loaded object: {obj}")
                except Exception as e:
                    logger.error(f"Failed to parse object of type {typ} from {path}: {e}")
                    raise
            elif not ignore_unknown:
                logger.error(f"Unknown type: {typ!r} in {path}")
                raise ValueError(f"Unknown type: {typ!r}")
        return result
