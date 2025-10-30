# game_actions.py (예시)
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from enums import PartyID

class ActionTypeEnum(str, Enum):
    RESERVE = "RESERVE"
    COUP = "COUP"
    COUNTER_COUP = "COUNTER_COUP"
    DEMONSTRATION = "DEMONSTRATION"
    FIGHT = "FIGHT"
    MOBILIZE = "MOBILIZE"
    TAKE_CONTROL = "TAKE_CONTROL"
    FOREIGN_AFFAIRS = "FOREIGN_AFFAIRS"

class PlayOptionEnum(str, Enum):
    EVENT = "EVENT"
    DEBATE = "DEBATE"
    ACTION = "ACTION"

class Move(BaseModel):
    player_id: PartyID

    # 각 액션에 필요한 파라미터들 (옵셔널)
    card_id: Optional[str] = None
    play_option: Optional[PlayOptionEnum] = None
    card_action_type: Optional[ActionTypeEnum] = None

    # 액션 공통 필드
    target: Optional[str] = None
