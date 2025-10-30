from enum import Enum, auto

class Faction(str, Enum):
    """
    유닛의 영구적인 소속 세력(정체성)을 정의합니다.
    """
    KPD = "KPD"
    SPD = "SPD"
    DNVP = "DNVP"
    GOVERNMENT = "GOVERNMENT"

class PartyID(str, Enum):
    """
    플레이 가능한 정당의 고유 ID.
    parties.json의 'id'와 일치해야 함.
    """
    KPD = "KPD"
    SPD = "SPD"
    DNVP = "DNVP"
    ZENTRUM = "ZENTRUM"

class GamePhase(Enum):
    SETUP = auto()
    AGENDA_PHASE_START = auto()
    AGENDA_PHASE_AWAIT_CHOICES = auto()
    IMPULSE_PHASE_START = auto()
    IMPULSE_PHASE_AWAIT_MOVE = auto()
    IMPULSE_PHASE_AWAIT_REACTION = auto()
    REACTION_WINDOW_GATHERING = auto() # 리액션 접수 중
    REACTION_WINDOW_AWAIT_CHOICE = auto() # 특정 플레이어의 응답 대기 중
    REACTION_CHAIN_RESOLVING = auto() # 스택 처리 중
    POLITICS_PHASE = auto()
    GAME_OVER = auto()