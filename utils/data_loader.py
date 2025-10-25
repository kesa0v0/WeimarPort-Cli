from enum import Enum
import json
import logging
from typing import Any, Dict, Type, Optional, List, Protocol

from pydantic import BaseModel, ValidationError, ValidationError

from datas import IssueData, PartyData, CityData, SocietyData, ThreatData, UnitData



logger = logging.getLogger(__name__)

class ToDictProto(Protocol):
    def to_dict(self) -> Dict[str, Any]:
        ...

DEFAULT_TYPE_MAP: Dict[str, Type[Any]] = {
    "PartyData": PartyData,
    "CityData": CityData,
    "UnitData": UnitData,
    "ThreatData": ThreatData,
    "SocietyData": SocietyData,
    "IssueData": IssueData
}

class DataLoader:
    def __init__(self, type_map: Optional[Dict[str, Type[BaseModel]]] = None):
        self.type_map = dict(DEFAULT_TYPE_MAP)
        if type_map:
            self.type_map.update(type_map)

    def load(self, path: str) -> Dict[str, BaseModel]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
                if not isinstance(payload, list): # ⭐️ 최상위가 리스트인지 확인
                    raise TypeError(f"Expected a list of objects in {path}, got {type(payload)}")
        except FileNotFoundError:
            logger.error(f"Data file not found: {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {path}: {e}")
            raise
        except TypeError as e:
            logger.error(e)
            raise


        result: Dict[str, BaseModel] = {}
        for index, item in enumerate(payload): # ⭐️ 인덱스 추가 (오류 추적용)
            if not isinstance(item, dict) or "type" not in item or "data" not in item:
                logger.error(f"Invalid item format at index {index} in {path}. Skipping item: {item}")
                continue # ⭐️ 잘못된 형식의 아이템 건너뛰기

            typ = item["type"]
            data = item["data"]

            cls = self.type_map.get(typ)
            if not cls:
                logger.warning(f"Unknown type '{typ}' at index {index} in {path}. Skipping item.")
                continue # ⭐️ 모르는 타입 건너뛰기

            try:
                # ⭐️ Pydantic 모델로 직접 파싱 및 유효성 검사!
                obj = cls.parse_obj(data)
                
                # ID 필드가 있는지 확인 (Pydantic 모델에 id가 정의되어 있어야 함)
                obj_id = getattr(obj, "id", None) 
                # ⭐️ Pydantic 모델의 id 타입이 Enum일 수 있으므로 .value 사용 고려
                if isinstance(obj_id, Enum): 
                    obj_id = obj_id.value

                if not obj_id or not isinstance(obj_id, str):
                     logger.error(f"Object of type {typ} at index {index} missing valid 'id' in {path}. Skipping item: {data}")
                     continue

                if obj_id in result:
                    logger.warning(f"Duplicate id '{obj_id}' found at index {index} in {path}. Overwriting previous entry.")
                
                result[obj_id] = obj
                logger.debug(f"Loaded object: {obj}")
    
            except ValidationError as e:
                # ⭐️ Pydantic 유효성 검사 실패 시 오류 로깅 및 건너뛰기
                logger.error(f"Validation failed for type '{typ}' at index {index} in {path}. Skipping item. Errors: {e.errors()}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error parsing object of type {typ} at index {index} in {path}: {e}. Skipping item: {data}")
                continue

        return result