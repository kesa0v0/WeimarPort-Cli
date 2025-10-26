

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
        self.setup_state = None  # type: SetupState | None
        self.scenario = None
        self.placement_order = [
            PartyID.SPD,
            PartyID.ZENTRUM,
            PartyID.KPD,
            PartyID.DNVP
        ]
        # PLAYER_CHOICE_MADE 이벤트 구독
        self.bus.subscribe(game_events.PLAYER_CHOICE_MADE, self.handle_player_choice_made)

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
        성공 또는 실패 여부를 EventBus를 통해 View에 알립니다.
        """
        try:
            logger.debug(f"Handling scenario load request for scenario ID: {scenario.id}")
            self.scenario = scenario
            self.model.setup_game_from_scenario(scenario)
            # 기반 설치 단계 상태 초기화
            self.setup_state = SetupState(
                phase="base_placement",
                current_party_index=0,
                bases_placed_count=0
            )

            success_message = f"Scenario '{scenario.name}' loaded successfully."
            logger.info(success_message)
            self.bus.publish(game_events.UI_SHOW_MESSAGE, {"message": success_message})

            await self.start_initial_base_placement() # scenario 인자 제거 가능 (self.scenario 사용)

        except Exception as e:
            error_message = f"Failed to setup game from scenario: {e}"
            logger.exception(error_message)
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": error_message})
    
    async def start_initial_base_placement(self):
        """
        초기 기반 배치를 비동기적으로 처리합니다.
        """
        if not self.setup_state or self.setup_state["phase"] != "base_placement":
            logger.warning("Base placement phase is not active or setup_state is None.")
            return
        if not self.scenario:
             logger.error("Scenario not loaded, cannot start base placement.")
             return

        while self.setup_state["phase"] == "base_placement": # 루프 조건 변경
            current_index = self.setup_state["current_party_index"]

            if current_index >= len(self.placement_order):
                logger.info("All parties base placement complete. Starting first turn.")
                self.setup_state["phase"] = "setup_complete"
                self.start_first_turn()
                break # 루프 종료

            current_party_id = self.placement_order[current_index]
            try:
                # ⭐️ self.scenario 사용
                bases_to_place = self.scenario.initial_party_setup[current_party_id].city_bases
            except (KeyError, AttributeError): # Pydantic 모델 접근 시 AttributeError 가능성
                logger.error(f"Invalid bases_to_place info for party {current_party_id}.")
                # 오류 처리: 루프 중단 또는 다음 단계로 강제 이동 등
                self.setup_state["phase"] = "error" # 예시: 에러 상태로 변경
                break
            placed_count = self.setup_state["bases_placed_count"]

            if placed_count < bases_to_place:
                # 유효한 도시 목록 계산
                valid_cities = self.model.get_valid_base_placement_cities(current_party_id)
                if not valid_cities:
                    logger.warning(f"No valid cities for {current_party_id} to place base {placed_count+1}/{bases_to_place}. Skipping party.")
                    # 다음 정당으로 강제 이동
                    self.setup_state["current_party_index"] += 1
                    self.setup_state["bases_placed_count"] = 0
                    continue # 다음 루프 반복

                context = {
                    "action": "initial_base_placement",
                    "party": current_party_id,
                    "remaining": bases_to_place - placed_count,
                    "bases_to_place": bases_to_place,
                    "prompt": f"기반을 배치할 도시를 선택하세요 ({placed_count + 1}/{bases_to_place})"
                }
                options = valid_cities

                # ⭐️ 해당 플레이어 에이전트 찾기
                agent = self.agents.get(current_party_id)
                if not agent:
                    logger.error(f"Agent not found for party {current_party_id}. Skipping placement.")
                    # 오류 처리
                    self.setup_state["phase"] = "error"
                    break

                # ⭐️ 에이전트에게 직접 선택 요청 (await 사용)
                try:
                    selected_city = await agent.get_choice(options, context)
                except Exception as e:
                     logger.error(f"Error getting choice from agent {current_party_id}: {e}")
                     # 오류 처리 (예: 랜덤 선택으로 대체, 게임 중단 등)
                     self.setup_state["phase"] = "error"
                     break


                # 선택 결과 처리 (Model 업데이트)
                if selected_city in valid_cities:
                    success = self.model._place_party_base(current_party_id, selected_city)
                    if success:
                        self.setup_state["bases_placed_count"] += 1
                        # (선택적) 기반 배치 성공 메시지 발행
                        self.bus.publish(game_events.UI_SHOW_MESSAGE, {
                            "message": f"{current_party_id} placed base in {selected_city} ({self.setup_state['bases_placed_count']}/{bases_to_place})."
                            # "target_party_id": current_party_id.value # 특정 플레이어에게만 보낼 경우
                        })
                    else:
                        # 배치 실패 시 (예: 동시에 다른 요청으로 인해 자리가 찬 경우 - 거의 없음)
                        logger.warning(f"Failed to place base for {current_party_id} in {selected_city} even after selection.")
                        # 이 경우 다시 선택 요청을 보내거나 오류 처리 필요
                        pass # 현재는 그냥 다음 루프 반복 (재시도)

                else:
                    logger.warning(f"Agent {current_party_id} returned invalid choice '{selected_city}'. Requesting again.")
                    # 유효하지 않은 선택 시, 루프를 계속 돌며 다시 요청 (AI가 잘못된 값을 줄 경우 대비)
                    continue

            else:
                # 해당 정당 배치 완료, 다음 정당으로 이동
                self.setup_state["current_party_index"] += 1
                self.setup_state["bases_placed_count"] = 0
                # 루프 상단에서 다음 정당 처리

            # ⭐️ 다른 비동기 작업에 실행 기회 주기 (선택적)
            await asyncio.sleep(0)

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
        if action == "remove_opponent_base":
            self._handle_remove_opponent_base_choice(data)
        # 추가 액션은 elif로 확장
        else:
            logger.warning(f"PLAYER_CHOICE_MADE: 알 수 없는 action '{action}'")

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
        