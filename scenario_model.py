# scenario_models.py (신규 생성)
import logging
from typing import ClassVar, Dict, List, Optional, Set
from pydantic import BaseModel, Field, ValidationError, field_validator, validator

from datas import GameKnowledge
from enums import PartyID # PartyID Enum 임포트
# ⭐️ GameKnowledge 모델이 정의된 파일을 임포트해야 합니다.
# from datas import GameKnowledge 

logger = logging.getLogger(__name__)

# 내부 구조를 위한 모델들
class StartingTrackers(BaseModel):
    round: int = 1
    foreign_affairs_track: str # TODO: Enum으로 만들거나 유효성 검사 추가
    economy_track: int

class StartingGovernment(BaseModel):
    chancellor: PartyID
    parties: Set[PartyID]

class RandomThreatTask(BaseModel):
    threat_id: str # ⭐️ ThreatData의 id와 일치하는지 검증 필요
    count: int
    unique_cities: bool = False

class InitialThreats(BaseModel):
    dr_box: List[str] = Field(default_factory=list) # 기본값 빈 리스트
    specific_cities: Dict[str, List[str]] = Field(default_factory=dict)
    random_cities: List[RandomThreatTask] = Field(default_factory=list)

class InitialPartySetupDetail(BaseModel):
    city_bases: int
    parliament_seats: int

# 최상위 시나리오 모델
class ScenarioModel(BaseModel):
    game_knowledge: ClassVar[GameKnowledge]

    id: str
    name: str
    starting_trackers: StartingTrackers
    starting_president: str # TODO: Enum 또는 유효성 검사 추가
    starting_government: StartingGovernment
    starting_minor_parties: Dict[str, PartyID] # Key: MinorPartyID(str), Value: Controlling PartyID
    initial_threats: InitialThreats
    initial_party_setup: Dict[PartyID, InitialPartySetupDetail] # Key: PartyID Enum

    # (game_knowledge 기반 유효성 검사는 외부 함수에서 수행)

    # 다른 필드에 대한 유효성 검사기 추가 가능...