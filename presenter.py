

import asyncio
import logging
from typing import Any, TypedDict
from enums import PartyID
from event_bus import EventBus
import game_events
from models import GameModel
from scenario_model import ScenarioModel
from player_agent import IPlayerAgent


logger = logging.getLogger(__name__)



class SetupState(TypedDict):
    phase: str
    current_party_index: int
    bases_placed_count: int

from game_action import Move

class GamePresenter:
    def __init__(self, bus: EventBus, model: GameModel, agents: dict[PartyID, IPlayerAgent]):
        self.bus = bus
        self.model = model
        self.agents = agents
        # PLAYER_CHOICE_MADE 이벤트 구독
        self.bus.subscribe(game_events.PLAYER_CHOICE_MADE, self.handle_player_choice_made)
        # REQUEST_PLAYER_CHOICE 이벤트 구독 (Model -> Presenter)
        self.bus.subscribe(game_events.REQUEST_PLAYER_CHOICE, self.handle_request_player_choice)
        # 데이터 변경 및 게임 흐름 이벤트 구독 추가
        self.bus.subscribe(game_events.DATA_PARTY_BASE_PLACED, self.handle_party_base_placed)
        self.bus.subscribe(game_events.SETUP_PHASE_COMPLETE, self.handle_setup_phase_complete)

    def handle_move(self, move: Move):
        """
        main.py 등에서 전달받은 Move 객체를 실행합니다.
        """
        try:
            result = self.model.execute_move(move)
            self.bus.publish(game_events.UI_SHOW_MESSAGE, {"message": f"Action executed: {move.action_type}"})
            # 필요시 result에 따라 추가 이벤트 발행 가능
        except Exception as e:
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": f"Move 실행 중 오류: {e}"})

    async def handle_load_scenario(self, scenario: ScenarioModel):
        """
        검증된 ScenarioModel 객체를 Model에 전달하여 게임 상태 설정을 위임합니다.
        Model이 설정 과정에서 필요한 이벤트를 발생시킬 것입니다.
        """
        try:
            logger.debug(f"Handling scenario load request for scenario ID: {scenario.id}")
            self.model.setup_game_from_scenario(scenario)

        except Exception as e:
            error_message = f"Failed to setup game from scenario: {e}"
            logger.exception(error_message)
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": error_message})

    def handle_request_player_choice(self, data: dict):
        """
        Model로부터 플레이어의 선택이 필요하다는 요청을 동기적으로 받아,
        실제 비동기 선택 로직을 백그라운드 작업으로 스케줄링합니다.
        """
        async def do_choice():
            player_id = data.get("player_id")
            options = data.get("options")
            context = data.get("context")

            agent = self.agents.get(player_id)
            if not agent:
                logger.error(f"Agent not found for party {player_id}. Cannot get choice.")
                return

            try:
                # Agent에게 비동기적으로 선택을 요청
                selected_option = await agent.get_choice(options, context)

                # Agent의 선택을 다른 이벤트로 발행하여 handle_player_choice_made에서 처리
                self.bus.publish(game_events.PLAYER_CHOICE_MADE, {
                    "player_id": player_id,
                    "selected_option": selected_option,
                    "context": context
                })
            except Exception as e:
                logger.error(f"Error getting choice from agent {player_id}: {e}")
                self.bus.publish(game_events.UI_SHOW_ERROR, {"error": f"에이전트 선택 중 오류 발생: {e}"})
        
        # 비동기 작업을 이벤트 루프에서 실행하도록 스케줄링
        asyncio.create_task(do_choice())


    def handle_player_choice_made(self, data: dict):
        """
        PLAYER_CHOICE_MADE 이벤트 핸들러. Agent의 선택을 Model에 전달합니다.
        """
        context = data.get("context", {})
        action = context.get("action")

        if not action:
            logger.error("PLAYER_CHOICE_MADE: context에 action이 없습니다.")
            return

        # 액션별 분기 처리
        if action == "initial_base_placement":
            player_id = data.get("player_id")
            selected_city = data.get("selected_option")
            self.model.resolve_initial_base_placement(player_id, selected_city)

        elif action == "resolve_place_base":
            self.model._resolve_place_base_choice(data)
        else:
            logger.warning(f"PLAYER_CHOICE_MADE: 알 수 없는 action '{action}'")

    def handle_party_base_placed(self, data: dict):
        """기반 배치 결과를 UI에 표시합니다."""
        party_id = data.get("party_id")
        city_id = data.get("city_id")
        self.bus.publish(game_events.UI_SHOW_MESSAGE, {
            "message": f"[{party_id.value}] placed a base in {city_id}."
        })

    def handle_setup_phase_complete(self, data: dict):
        """초기 설정 완료를 UI에 알립니다."""
        self.bus.publish(game_events.UI_SHOW_MESSAGE, {
            "message": "Initial setup is complete. The first round begins."
        })
        