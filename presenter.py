

import logging
from typing import Any
from enums import PartyID
from event_bus import EventBus
import game_events
from models import GameModel
from scenario_model import ScenarioModel


logger = logging.getLogger(__name__)


class GamePresenter:
    def __init__(self, bus: EventBus, model: GameModel):
        self.bus = bus
        self.model = model
        self.setup_state = None
        self.placement_order = [
            PartyID.SPD,
            PartyID.ZENTRUM,
            PartyID.KPD,
            PartyID.DNVP
        ]
        # PLAYER_CHOICE_MADE 이벤트 구독
        self.bus.subscribe(game_events.PLAYER_CHOICE_MADE, self.handle_player_choice_made)
        
    def handle_show_status(self):
        data = self.model.get_status_data()
        self.bus.publish(game_events.UI_SHOW_STATUS, data)

    def handle_load_scenario(self, scenario: ScenarioModel):
        """
        검증된 ScenarioModel 객체를 Model에 전달하여 게임 상태 설정을 위임합니다.
        성공 또는 실패 여부를 EventBus를 통해 View에 알립니다.
        """
        try:
            logger.debug(f"Handling scenario load request for scenario ID: {scenario.id}")
            self.model.setup_game_from_scenario(scenario)
            # 기반 설치 단계 상태 초기화
            self.setup_state = {
                "phase": "base_placement",
                "current_party_index": 0,
                "bases_placed_count": 0
            }
            self.scenario = scenario  # 이후 응답 루프에서 사용
            success_message = f"Scenario '{scenario.name}' loaded successfully."
            logger.info(success_message)
            self.bus.publish(game_events.UI_SHOW_MESSAGE, {"message": success_message})
        except Exception as e:
            error_message = f"Failed to setup game from scenario: {e}"
            logger.exception(error_message)
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": error_message})

    def start_initial_base_placement(self, scenario: ScenarioModel):
        """
        초기 기반 배치 요청-응답 루프를 처리합니다.
        """
        if not self.setup_state or self.setup_state.get("phase") != "base_placement":
            logger.warning("Base placement phase is not active.")
            return

        try:
            current_index = int(self.setup_state["current_party_index"])
        except (KeyError, ValueError, TypeError):
            logger.error("Invalid current_party_index in setup_state.")
            return

        if current_index >= len(self.placement_order):
            logger.info("All parties base placement complete. Starting first turn.")
            self.setup_state = {"phase": "setup_complete"}
            self.start_first_turn()
            return

        current_party_id = self.placement_order[current_index]
        try:
            bases_to_place = int(scenario.initial_party_setup[current_party_id].city_bases)
        except (KeyError, ValueError, TypeError, AttributeError):
            logger.error(f"Invalid bases_to_place for party {current_party_id}.")
            return
        try:
            placed_count = int(self.setup_state["bases_placed_count"])
        except (KeyError, ValueError, TypeError):
            logger.error("Invalid bases_placed_count in setup_state.")
            return

        if placed_count < bases_to_place:
            # 유효한 도시 목록 계산
            get_valid_cities = getattr(self.model, "get_valid_base_placement_cities", None)
            if callable(get_valid_cities):
                valid_cities = get_valid_cities(current_party_id)
            else:
                logger.warning("GameModel.get_valid_base_placement_cities() is not implemented.")
                valid_cities = []
            context = {
                "action": "initial_base_placement",
                "party": current_party_id,
                "remaining": bases_to_place - placed_count
            }
            options = valid_cities
            self.bus.publish(
                game_events.REQUEST_PLAYER_CHOICE,
                {"context": context, "options": options}
            )
            # 응답을 기다림 (응답 핸들러에서 bases_placed_count 증가 및 재호출 필요)
        else:
            # 해당 정당 배치 완료, 다음 정당으로 이동
            self.setup_state["current_party_index"] = str(current_index + 1)
            self.setup_state["bases_placed_count"] = "0"
            # 다음 정당 배치 시작
            self.start_initial_base_placement(scenario)

    def handle_player_choice_made(self, data: dict):
        """
        PLAYER_CHOICE_MADE 이벤트 핸들러. context의 action에 따라 분기 처리.
        """
        context = data.get("context", {})
        action = context.get("action")
        if not action:
            logger.error("PLAYER_CHOICE_MADE: context에 action이 없습니다.")
            return

        # 액션별 분기 처리
        if action == "initial_base_placement":
            self._handle_initial_base_placement_choice(data)
        elif action == "remove_opponent_base":
            self._handle_remove_opponent_base_choice(data)
        # 추가 액션은 elif로 확장
        else:
            logger.warning(f"PLAYER_CHOICE_MADE: 알 수 없는 action '{action}'")

    def _handle_initial_base_placement_choice(self, data: dict):
        """
        초기 기반 배치 선택 응답 처리
        """
        if self.setup_state is None:
            logger.error("setup_state is None.")
            return
        selected_city = data.get("selected_option")
        if not selected_city:
            logger.error("selected_city is None.")
            return
        
        try:
            current_party_index = int(self.setup_state["current_party_index"])
            current_party_id = self.placement_order[current_party_index]
        except Exception as e:
            logger.error(f"Error getting current_party_id: {e}")
            return
        
        # 기반 배치
        place_base = self.model._place_party_base(current_party_id, selected_city)
        if callable(place_base):
            place_base(current_party_id, selected_city)
        else:
            logger.error("GameModel._place_party_base() is not implemented.")
            return
        
        # 배치 카운트 증가
        try:
            self.setup_state["bases_placed_count"] = int(self.setup_state["bases_placed_count"]) + 1 # type: ignore
        except Exception as e:
            logger.error(f"Error incrementing bases_placed_count: {e}")
            return
        
        # 다음 기반 배치 루프 호출
        if hasattr(self, "scenario"):
            self.start_initial_base_placement(self.scenario)
        else:
            logger.error("self.scenario is not set in presenter.")

    def _handle_remove_opponent_base_choice(self, data: dict):
        """
        상대 기반 제거 선택 응답 처리 (샘플)
        """
        # TODO: 실제 게임 로직에 맞게 구현
        selected_base = data.get("selected_option")
        logger.info(f"선택된 상대 기반: {selected_base}")
        # 이후 필요한 게임 상태 변경 및 이벤트 발행 등 구현

    def start_first_turn(self):
        """
        첫 번째 턴을 시작합니다.
        """
        print("Start First Turn <<")
        # 몬가몬가 잘못됨...
        