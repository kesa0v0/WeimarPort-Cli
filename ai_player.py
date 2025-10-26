# ai_agent.py
import random
import asyncio
from typing import Any, List, Dict
from player_agent import IPlayerAgent
from models import GameModel
# from game_actions import Move

class RandomAIAgent(IPlayerAgent):

    async def get_next_command(self, game_model: GameModel) -> str:
        # AI는 CommandParser가 필요 없음. 바로 Model에 접근 가능해야 함.
        # 이 구조에서는 AI도 일단 명령어를 반환하고 Parser가 처리하게 함.
        # TODO: get_valid_moves 구현 필요
        valid_moves_placeholder = ["status", "pass"] # 실제로는 model.get_valid_moves 호출
        chosen_move_placeholder = random.choice(valid_moves_placeholder)
        print(f"[AI {self.party_id}] 결정: {chosen_move_placeholder}")
        # AI 계산 시간 시뮬레이션 (선택적)
        await asyncio.sleep(0.1)
        return chosen_move_placeholder # 예시: 일단 명령어 문자열 반환

    async def get_choice(self, options: List[Any], context: Dict[str, Any]) -> Any:
        chosen_option = random.choice(options)
        print(f"[AI {self.party_id}] 선택 ({context.get('action', '')}): {chosen_option}")
        await asyncio.sleep(0.1)
        return chosen_option

    def receive_message(self, event_type: str, data: Dict[str, Any]):
        # AI는 메시지를 로깅하거나 학습 데이터로 사용할 수 있음
        # print(f"[AI {self.party_id} Log] {event_type}: {data}")
        pass # 단순 랜덤 AI는 메시지 무시