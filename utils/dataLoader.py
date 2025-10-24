import json
import logging
from typing import Any, Dict, Type, Optional, List, Protocol

from datas import PartyData, CityData, ThreatData, UnitData


logger = logging.getLogger(__name__)

class ToDictProto(Protocol):
    def to_dict(self) -> Dict[str, Any]:
        ...

DEFAULT_TYPE_MAP: Dict[str, Type[Any]] = {
    "PartyData": PartyData,
    "CityData": CityData,
    "UnitData": UnitData,
    "ThreatData": ThreatData
}

class DataLoader:
    def __init__(self, type_map: Optional[Dict[str, Type[Any]]] = None, *, indent: int = 2):
        self.type_map = dict(DEFAULT_TYPE_MAP)
        if type_map:
            self.type_map.update(type_map)
        self.indent = indent

    def load(self, path: str, ignore_unknown: bool = True) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                logging.debug(f"{path} opened successfully.")
                payload = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            raise

        result: Dict[str, Any] = {}
        for item in payload:
            try:
                # `typ`이 없거나 잘못된 경우 처리
                typ = item.get("type")
                if not typ:
                    logger.error(f"Missing 'type' field in item: {item}")
                    continue

                # `data`가 없거나 잘못된 경우 처리
                data = item.get("data", {})
                if not isinstance(data, dict):
                    logger.error(f"Invalid 'data' field in item: {item}")
                    continue

                # `cls`가 type_map에 없는 경우 처리
                cls = self.type_map.get(typ)
                if not cls:
                    if not ignore_unknown:
                        logger.error(f"Unknown type: {typ!r} in {path}")
                        raise ValueError(f"Unknown type: {typ!r}")
                    else:
                        logger.warning(f"Ignored unknown type: {typ!r} in {path}")
                        continue

                # 객체 생성 시 발생하는 오류 처리
                try:
                    obj = cls.from_dict(data)
                    obj_id = getattr(obj, "id", None)
                    if not obj_id:
                        logger.error(f"Object of type {typ} missing 'id': {data}")
                        continue
                    if obj_id in result:
                        logger.warning(f"Duplicate id '{obj_id}' found in {path}")
                    result[obj_id] = obj
                    logger.debug(f"Loaded object: {obj}")
                except Exception as e:
                    logger.error(f"Failed to parse object of type {typ} with data {data} from {path}: {e}")
                    continue

            except Exception as e:
                logger.error(f"Unexpected error while processing item {item} from {path}: {e}")
                continue

        return result