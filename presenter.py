

import logging
from typing import Any
from event_bus import EventBus
import game_events
from models import GameModel
from scenario_model import ScenarioModel


logger = logging.getLogger(__name__)


class GamePresenter:
    def __init__(self, bus: EventBus, model: GameModel):
        self.bus = bus
        self.model = model

    def handle_show_status(self):
        data = self.model.get_status_data()
        self.bus.publish(game_events.UI_SHOW_STATUS, data)

    def handle_load_scenario(self, scenario: ScenarioModel):
        """
        검증된 ScenarioModel 객체를 Model에 전달하여 게임 상태 설정을 위임합니다.
        성공 또는 실패 여부를 EventBus를 통해 View에 알립니다.
        """
        try:
            # 객체의 속성(예: scenario.id)에 직접 접근
            logger.debug(f"Handling scenario load request for scenario ID: {scenario.id}")
            # 1. Model의 설정 메서드 호출 (Model도 ScenarioModel을 받도록 수정 필요)
            self.model.setup_game_from_scenario(scenario)

            # 2. 성공 메시지 발행 (View에게 알림)
            # 객체의 속성(예: scenario.name)에 직접 접근
            success_message = f"Scenario '{scenario.name}' loaded successfully."
            logger.info(success_message)
            self.bus.publish(game_events.UI_SHOW_MESSAGE, {"message": success_message})

        except Exception as e:
            # 3. 실패 시 오류 메시지 발행 (View에게 알림)
            error_message = f"Failed to setup game from scenario: {e}"
            logger.exception(error_message)
            self.bus.publish(game_events.UI_SHOW_ERROR, {"error": error_message})