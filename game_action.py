# game_actions.py (예시)
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from enums import PartyID

class ActionTypeEnum(str, Enum):
    PLAY_CARD = "PLAY_CARD"
    COUP = "COUP"
    DEMONSTRATION = "DEMONSTRATION"
    PASS_TURN = "PASS_TURN"
    # ... 다른 액션 타입 ...

class PlayOptionEnum(str, Enum):
    EVENT = "EVENT"
    DEBATE = "DEBATE"
    ACTION = "ACTION"

class Move(BaseModel):
    player_id: PartyID
    action_type: ActionTypeEnum

    # 각 액션에 필요한 파라미터들 (옵셔널)
    card_id: Optional[str] = None
    play_option: Optional[PlayOptionEnum] = None
    target_city: Optional[str] = None
    # ... 다른 파라미터 (예: target_unit_id, choice_made 등) ...

    # 유효성 검사기 추가 가능 (예: COUP 액션은 target_city가 필수)