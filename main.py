from colorama import Fore, Style, init as init_colorama
import logging

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
    model, view, presenter = installer.start_game()

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