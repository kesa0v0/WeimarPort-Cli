# scenario_models.py (신규 생성)
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator, validator

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
    parties: List[PartyID]

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
    id: str
    name: str
    starting_trackers: StartingTrackers
    starting_president: str # TODO: Enum 또는 유효성 검사 추가
    starting_government: StartingGovernment
    starting_minor_parties: Dict[str, PartyID] # Key: MinorPartyID(str), Value: Controlling PartyID
    initial_threats: InitialThreats
    initial_party_setup: Dict[PartyID, InitialPartySetupDetail] # Key: PartyID Enum

    # ⭐️ 추가 유효성 검사기 (선택적이지만 강력함)
    @field_validator('initial_threats')
    def validate_threat_ids(cls, v: InitialThreats, values):
        # GameKnowledge 인스턴스에 접근할 방법이 필요합니다.
        # 예를 들어, 로더 함수에서 검증을 수행하거나,
        # 전역 변수 또는 클래스 변수로 GameKnowledge를 참조할 수 있게 합니다.
        
        # known_threat_ids = set(game_knowledge.threats.keys()) # 예시
        known_threat_ids = {"POVERTY", "UNREST", "COUNCILS", "BLOCKADE", "INFLATION"} # 임시 하드코딩

        all_threats = v.dr_box + [t for threats in v.specific_cities.values() for t in threats] + \
                      [task.threat_id for task in v.random_cities]
                      
        for threat_id in all_threats:
             if threat_id not in known_threat_ids:
                 raise ValueError(f"Unknown threat_id '{threat_id}' found in scenario.")
        return v

    @field_validator('initial_threats')
    def validate_city_ids(cls, v: InitialThreats, values):
         # known_city_ids = set(game_knowledge.cities.keys()) # 예시
         known_city_ids = {"berlin", "munich", "essen", "hamburg"} # 임시 하드코딩
         for city_id in v.specific_cities.keys():
             if city_id not in known_city_ids:
                 raise ValueError(f"Unknown city_id '{city_id}' found in initial_threats.")
         return v

    # 다른 필드에 대한 유효성 검사기 추가 가능...