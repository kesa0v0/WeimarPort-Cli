
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
        
        self.agents = {
            PartyID.SPD: ConsoleAgent(PartyID.SPD),
            PartyID.ZENTRUM: RandomAIAgent(PartyID.ZENTRUM),
            PartyID.KPD: ConsoleAgent(PartyID.KPD),
            PartyID.DNVP: RandomAIAgent(PartyID.DNVP),
        }
        agent_types = {pid.name: type(agent).__name__ for pid, agent in self.agents.items()}
        self.logger.info(f"Player agents assigned: {agent_types}")

        self.installer = GameManager()
        start_result = self.installer.start_game(self.agents)
        if start_result is None:
            self.logger.error("게임을 시작하지 못했습니다.")
            exit(1)
        self.model, self.presenter = start_result

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

    async def run(self):
        # 시나리오 선택
        while True:
            print("\n=== 시나리오 선택 ===")
            print("1. 기본 시나리오 로드")
            user_input = input("시나리오를 선택하세요: ").strip()
            if user_input.lower() == '1':
                scenario_file = "data/scenarios/main_scenario.json"
                await self.installer.load_scenario(scenario_file)
                self.logger.info("기본 시나리오가 로드되었습니다.")
                break
            else:
                print(f"{Fore.RED}[ERROR]{Fore.RESET} 유효한 시나리오 번호를 입력하세요.")

        # 초기 설정(기반 배치 등)이 완료될 때까지 대기합니다.
        self.logger.info("Waiting for initial setup to complete...")
        while self.model.setup_phase_active:
            await asyncio.sleep(0.1)
        self.logger.info("Initial setup complete.")

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
                break

def main():
    app = GameApp()
    asyncio.run(app.run())

if __name__ == "__main__":
    main()