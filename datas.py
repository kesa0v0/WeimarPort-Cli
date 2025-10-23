from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass()
class PartyData:
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PartyData":
        return cls(**d)


@dataclass
class CityData:
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CityData":
        return cls(**d)


@dataclass
class UnitData:
    name: str
    strength: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UnitData":
        return cls(**d)