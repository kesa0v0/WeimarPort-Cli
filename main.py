from colorama import init as init_colorama
import logger

from gameManager import GameManager


# colorama 초기화
init_colorama(autoreset=True)
# 로거 초기화
logger.init_logger()

if __name__ == "__main__":
    gameManager = GameManager()