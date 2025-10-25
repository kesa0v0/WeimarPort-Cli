

from typing import Any
from event_bus import EventBus
import game_events
from models import GameModel


class GamePresenter:
    def __init__(self, bus: EventBus, model: GameModel):
        self.bus = bus
        self.model = model

    def handle_show_status(self):
        data = self.model.get_status_data()
        self.bus.publish(game_events.UI_SHOW_STATUS, data)

    def handle_load_scenario(self, scenario_data: Any):
        """
        Model에 시나리오 데이터를 전달하여 게임 상태 설정을 위임합니다.
        """
        try:
            

            
            # ⭐️ (선택적) 로딩 성공 이벤트를 발행하여 View에 알릴 수 있습니다.
            self.bus.publish(game_events.UI_SHOW_MESSAGE,
                             {"message": f"Scenario '{scenario_data['name']}' loaded successfully."})
        except Exception as e:
            # ⭐️ (선택적) 로딩 실패 이벤트를 발행할 수 있습니다.
            self.bus.publish(game_events.UI_SHOW_ERROR,
                             {"error": f"Failed to setup scenario: {e}"})