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


def handle_request_player_choice(data):
    options = data.get("options", [])
    context = data.get("context", {})
    prompt_str = context.get("prompt") or "선택하세요:"
    while True:
        print(f"\n{prompt_str}")
        for i, option in enumerate(options):
            print(f"  {i+1}. {option}")
        choice_str = input("번호 입력> ").strip()
        try:
            choice_index = int(choice_str) - 1
            if 0 <= choice_index < len(options):
                selected_option = options[choice_index]
                installer.bus.publish(
                    game_events.PLAYER_CHOICE_MADE,
                    {"selected_option": selected_option, "context": context}
                )
                break
            else:
                print(f"{Fore.RED}[ERROR]{Fore.RESET} 1부터 {len(options)} 사이의 번호를 입력하세요.")
        except ValueError:
            print(f"{Fore.RED}[ERROR]{Fore.RESET} 숫자를 입력하세요.")


if __name__ == "__main__":
    installer = GameManager()
    start_result = installer.start_game()
    if start_result is None:
        logger.error("게임을 시작하지 못했습니다.")
        exit(1)
    model, view, presenter = start_result

    installer.bus.subscribe(game_events.REQUEST_PLAYER_CHOICE, handle_request_player_choice)
    
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