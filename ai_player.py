# ai_agent.py
import random
import asyncio
from typing import Any, List, Dict
from game_action import Move
from player_agent import IPlayerAgent
from models import GameModel
# from game_actions import Move

class RandomAIAgent(IPlayerAgent):

    async def get_next_move(self, game_model: GameModel) -> 'Move':
        valid_moves = game_model.get_valid_moves(self.party_id)
        if not valid_moves:
            raise RuntimeError(f"No valid moves for AI {self.party_id}")
        chosen_move = random.choice(valid_moves)
        print(f"[AI {self.party_id}] 결정: {chosen_move}")
        await asyncio.sleep(0.1)
        return chosen_move

    async def get_choice(self, options: List[Any], context: Dict[str, Any]) -> Any:
        chosen_option = random.choice(options)
        print(f"[AI {self.party_id}] 선택 ({context.get('action', '')}): {chosen_option}")
        await asyncio.sleep(0.1)
        return chosen_option

    def receive_message(self, event_type: str, data: Dict[str, Any]):
        # AI는 메시지를 로깅하거나 학습 데이터로 사용할 수 있음
        # print(f"[AI {self.party_id} Log] {event_type}: {data}")
        pass # 단순 랜덤 AI는 메시지 무시