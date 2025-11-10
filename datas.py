from dataclasses import dataclass, asdict
from pydantic import BaseModel
from typing import Dict, Any, List, Mapping, Optional
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

class EffectChoice(BaseModel):
    """'선택지'를 위한 모델"""
    text: str # 플레이어에게 보여줄 텍스트
    effects: List['EffectData'] # 이 선택지를 골랐을 때 실행될 하위 효과 목록

class EffectData(BaseModel):
    """
    모든 이벤트 효과를 정의하는 범용 데이터 구조
    """
    type: str # "GAIN_VP", "PLACE_BASE", "ASK_CHOICE", "APPLY_CONDITION" 등
    
    # --- 대상 (Target) ---
    target: Optional[str] = "SELF" # "SELF", "OPPONENTS", "ALL_PLAYERS", "TARGET_CITY", "CITY_CHOICE"
    
    # --- 값 (Value) ---
    amount: Optional[int] = 1
    threat_id: Optional[str] = None
    unit_id: Optional[str] = None
    
    # --- 기본 행동 (Basic Actions) ---
    action_type: Optional[str] = None # "COUP", "DEMONSTRATION" 등
    
    # --- 조건부 (Conditions) ---
    condition: Optional[Dict[str, Any]] = None # {"type": "HAS_THREAT", "target": "berlin", "threat_id": "unrest"}
    effects_if_true: Optional[List['EffectData']] = None
    effects_if_false: Optional[List['EffectData']] = None
    
    # --- 선택지 (Choices) ---
    prompt: Optional[str] = None
    choices: Optional[List[EffectChoice]] = None
    
    # --- 지연/지속 (Delayed/Persistent) ---
    trigger: Optional[str] = None # "END_OF_ROUND", "START_OF_TURN"
    duration: Optional[str] = None # "THIS_ROUND", "PERMANENT"
    modifier_id: Optional[str] = None # "KPD_COUP_BONUS"

# Pydantic이 'EffectData' 내부에서 자신을 참조할 수 있도록 업데이트
EffectChoice.model_rebuild()
EffectData.model_rebuild()

class CardData(BaseModel):
    id: str
    desc_id: str
    
    action_point_main: int
    action_point_sub: int

    events: List[EffectData]

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
    party: Dict[PartyID, PartyData]
    cities: Dict[str, CityData]
    units: Dict[str, UnitData]
    threat: Dict[str, ThreatData]
    societies: Dict[str, SocietyData] = {}
    issues: Dict[str, IssueData] = {}
    minor_parties: Dict[str, MinorPartyData] = {}
    party_cards: Dict[str, PartyCardData] = {}
    timeline_cards: Dict[str, TimelineCardData] = {}