from dataclasses import dataclass, asdict
from pydantic import BaseModel
from typing import Dict, Any, List, Mapping
from enum import Enum
import logging

from enums import Faction, PartyID


logger = logging.getLogger(__name__)


def _enum_to_value(e: Enum | Any) -> Any:
    """Enum이면 value 반환, 아니면 그대로 반환"""
    return e.value if isinstance(e, Enum) else e

def _enum_from_value(enum_cls, v: Any):
    """value나 name 또는 이미 enum인 경우 enum 인스턴스로 변환"""
    if v is None:
        return None
    if isinstance(v, enum_cls):
        return v
    try:
        # 먼저 value로 변환 시도
        return enum_cls(v)
    except Exception:
        try:
            # value 실패하면 name으로 시도
            return enum_cls[v]
        except Exception:
            raise ValueError(f"Cannot convert {v!r} to {enum_cls}")


class PartyData(BaseModel):
    id: PartyID
    party_color: str


class MinorPartyData(BaseModel):
    id: str

class CardData(BaseModel):
    id: str
    desc_id: str
    
    action_point_main: int
    action_point_sub: int

    events: str # TODO: 이벤트 구조체로 변경 필요

    is_removed_on_use: bool
    
class PartyCardData(CardData):
    party_id: PartyID
    party_card_addition_type: str | None


class TimelineCardData(CardData):
    era: list[int]


class CityData(BaseModel):
    id: str
    max_party_bases: int
    city_dice_roll: int

class UnitData(BaseModel):
    id: str
    strength: int
    faction: Faction
    max_count: int

class ThreatData(BaseModel):
    id: str
    max_count: int
    

class SocietyData(BaseModel):
    id: str
    

class IssueData(BaseModel):
    id: str
    
    
class GameKnowledge(BaseModel):
    party: Dict[str, PartyData]
    cities: Dict[str, CityData]
    units: Dict[str, UnitData]
    threat: Dict[str, ThreatData]