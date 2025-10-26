
import asyncio
from colorama import Fore, Style, init as init_colorama
import logging
from ai_player import RandomAIAgent
from console_agent import ConsoleAgent
from enums import PartyID
import game_events
import log
from command_parser import CommandParser
from game_manager import GameManager


class GameApp:
    def __init__(self):
        # colorama 및 로거 초기화
        init_colorama(autoreset=True)
        log.init_logger()
        self.logger = logging.getLogger(__name__)

        self.input_mode = "COMMAND"
        self.pending_choice_data = None

        self.installer = GameManager()
        start_result = self.installer.start_game()
        if start_result is None:
            self.logger.error("게임을 시작하지 못했습니다.")
            exit(1)
        self.model, self.presenter = start_result

        self.agents = {
            PartyID.SPD: ConsoleAgent(PartyID.SPD),
            PartyID.ZENTRUM: RandomAIAgent(PartyID.ZENTRUM),
            PartyID.KPD: ConsoleAgent(PartyID.KPD),
            PartyID.DNVP: RandomAIAgent(PartyID.DNVP),
        }
        agent_types = {pid.name: type(agent).__name__ for pid, agent in self.agents.items()}
        self.logger.info(f"Player agents assigned: {agent_types}")

        # EventBus <-> Agent 연결
        self.installer.bus.subscribe(game_events.REQUEST_PLAYER_CHOICE, self.handle_request_player_choice)
        self.installer.bus.subscribe(game_events.UI_SHOW_MESSAGE, lambda data: self.message_router("UI_SHOW_MESSAGE", data))
        self.installer.bus.subscribe(game_events.UI_SHOW_ERROR, lambda data: self.message_router("UI_SHOW_ERROR", data))
        self.installer.bus.subscribe(game_events.UI_SHOW_STATUS, lambda data: self.message_router("UI_SHOW_STATUS", data))

    def message_router(self, event_type, data):
        target_party_id_str = data.get("target_party_id")
        if target_party_id_str:
            target_party_id = PartyID(target_party_id_str)
            if target_party_id in self.agents:
                self.agents[target_party_id].receive_message(event_type, data)
        else:
            for agent in self.agents.values():
                agent.receive_message(event_type, data)

    def handle_request_player_choice(self, data):
        context = data.get("context", {})
        options = data.get("options", [])
        party_id = context.get("party")
        if party_id is None:
            self.logger.error("REQUEST_PLAYER_CHOICE: party_id가 없습니다.")
            return
        agent = self.agents.get(party_id)
        if agent is None:
            self.logger.error(f"REQUEST_PLAYER_CHOICE: agent for {party_id} not found.")
            return

        async def choice_coroutine():
            selected_option = await agent.get_choice(options, context)
            self.presenter.bus.publish(game_events.PLAYER_CHOICE_MADE, {
                "context": context,
                "selected_option": selected_option
            })

        asyncio.create_task(choice_coroutine())

    async def run(self):
        # 시나리오 선택
        scenario_loaded = False
        while not scenario_loaded:
            print("\n=== 시나리오 선택 ===")
            print("1. 기본 시나리오 로드")
            user_input = input("시나리오를 선택하세요: ").strip()
            if user_input.lower() == '1':
                scenario_file = "data/scenarios/main_scenario.json"
                self.installer.load_scenario(scenario_file)
                self.logger.info("기본 시나리오가 로드되었습니다.")
                scenario_loaded = True
            else:
                self.logger.error("시나리오 로드 실패.")
                exit(1)

        # 초기 기반 배치 시작
        if self.presenter.scenario is None:
            self.logger.error("시나리오가 설정되지 않았습니다. 초기 기반 배치를 시작할 수 없습니다.")
            exit(1)
        self.presenter.start_initial_base_placement(self.presenter.scenario)

        self.logger.info("Entering main game loop...")
        while True:
            try:
                current_player_id = self.model.get_current_player()
                if not current_player_id:
                    self.logger.warning("Waiting for game to start or player to be set...")
                    await asyncio.sleep(0.1)
                    continue

                current_agent = self.agents[current_player_id]
                move = await current_agent.get_next_move(self.model)

                if hasattr(move, "action_type") and str(move.action_type).lower() in ("quit", "exit"):
                    self.logger.info("Exit command received.")
                    break

                self.presenter.handle_move(move)

                # TODO: 게임 종료 조건 확인 로직 추가

            except Exception as e:
                self.logger.exception(f"Error in main loop: {e}")

def main():
    app = GameApp()
    asyncio.run(app.run())

if __name__ == "__main__":
    main()