from dataclasses import dataclass, asdict
from typing import Dict, Any
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


@dataclass()
class PartyData:
    id: str
    party_color: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PartyData":
        return cls(**d)

@dataclass
class MinorPartyData:
    id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MinorPartyData":
        return cls(**d)

@dataclass
class CardData:
    id: str
    desc_id: str
    
    action_point_main: int
    action_point_sub: int

    events: str # TODO: 이벤트 구조체로 변경 필요

    is_removed_on_use: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CardData":
        return cls(**d)
    
@dataclass
class PartyCardData(CardData):
    party_id: PartyID

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["party_id"] = _enum_to_value(self.party_id)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PartyCardData":
        data = dict(d)
        data["party_id"] = _enum_from_value(PartyID, data.get("party_id"))
        return cls(**data)


@dataclass
class CityData:
    id: str
    max_party_bases: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CityData":
        return cls(**d)

@dataclass
class UnitData:
    id: str
    strength: int
    faction: Faction

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["faction"] = _enum_to_value(self.faction)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UnitData":
        data = dict(d)
        data["faction"] = _enum_from_value(Faction, data.get("faction"))
        return cls(**data)