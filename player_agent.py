# player_agent.py
import abc
from typing import Any, List, Dict, Optional
from game_action import Move
from models import GameModel # GameModel 임포트 가정
from enums import PartyID
# from game_actions import Move # Move 클래스 정의 필요

class IPlayerAgent(abc.ABC):
    """플레이어(인간 또는 AI)의 행동 결정을 위한 인터페이스"""

    def __init__(self, party_id: PartyID):
        self.party_id = party_id

    @abc.abstractmethod
    async def get_next_move(self, game_model: GameModel) -> 'Move':
        """
        현재 게임 상태를 보고 다음 행동(Move 객체)을 결정하여 반환합니다.
        """
        pass

    @abc.abstractmethod
    async def get_choice(self, options: List[Any], context: Dict[str, Any]) -> Any:
        """
        특정 상황(예: 기반 제거 대상 선택)에서 제시된 옵션 중 하나를 선택하여 반환합니다.
        context에는 선택에 필요한 추가 정보가 포함됩니다 (어떤 액션 중인지 등).
        """
        pass

    @abc.abstractmethod
    def receive_message(self, event_type: str, data: Dict[str, Any]):
        """
        게임 진행 중 발생하는 이벤트(로그, 상태 변경 알림 등)를 수신합니다.
        AI는 학습에 사용하거나 무시할 수 있고, 인간 플레이어는 화면에 출력할 수 있습니다.
        """
        pass