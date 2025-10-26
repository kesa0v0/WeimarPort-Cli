from colorama import Fore, Style, init as init_colorama
import logging

import game_events
import log
from command_parser import CommandParser
from game_manager import GameManager


# colorama 초기화
init_colorama(autoreset=True)
# 로거 초기화
log.init_logger()
logger = logging.getLogger(__name__)




if __name__ == "__main__":
    installer = GameManager()
    start_result = installer.start_game()
    if start_result is None:
        logger.error("게임을 시작하지 못했습니다.")
        exit(1)
        
    model, view, presenter = start_result

    # View가 직접 이벤트를 구독하므로 별도 구독 불필요

    while True:
        print(f"{Fore.YELLOW}{Style.BRIGHT}시나리오 선택{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}1. 기본 시나리오{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}5. 저장 파일 로드{Style.RESET_ALL}")
        select = input(f"{Fore.CYAN}{Style.BRIGHT}선택: {Style.RESET_ALL}").strip()

        if select == "1":
            scenario_file = "data/scenarios/main_scenario.json"
            if installer.load_scenario(scenario_file):
                logger.info("기본 시나리오가 로드되었습니다.")
                break
            else:
                logger.error("기본 시나리오 로드에 실패했습니다. 다시 시도해주세요.")
        elif select == "5":
            print(f"{Fore.RED}{Style.DIM}아직 구현되지 않은 기능입니다.{Style.RESET_ALL}")
            continue

    parser = CommandParser(presenter)


    while True:
        try:
            current_player_id = model.get_current_player()
            prompt = f"{Fore.GREEN}{Style.BRIGHT}[{current_player_id}] 명령> {Style.RESET_ALL}"
            user_input = input(prompt)

            if user_input.lower() in ('quit', 'exit'):
                logger.info("Exiting game.")
                break

            parser.parse_command(user_input, current_player_id)

        except EOFError: # (Ctrl+D 등으로 종료 시)
            logger.info("Exiting game (EOF).")
            break
        except KeyboardInterrupt: # (Ctrl+C로 종료 시)
            logger.info("Exiting game (Interrupt).")
            break