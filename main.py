import asyncio
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


# --- 상태 변수 및 데이터 저장소 ---
input_mode = "COMMAND"  # 현재 입력 모드: "COMMAND" 또는 "CHOICE"
pending_choice_data = None # 플레이어 선택 요청 데이터 저장


# --- 이벤트 핸들러 함수 ---
def handle_request_player_choice(data):
    """REQUEST_PLAYER_CHOICE 이벤트 핸들러: 입력 모드를 변경하고 데이터 저장"""
    global input_mode, pending_choice_data
    logger.debug(f"Received REQUEST_PLAYER_CHOICE: {data}")
    input_mode = "CHOICE"
    pending_choice_data = data
    # ⭐️ 실제 질문 출력은 메인 루프에서 처리

def handle_player_choice_made(data):
    """PLAYER_CHOICE_MADE 이벤트 핸들러: 입력 모드를 다시 COMMAND로 변경"""
    global input_mode, pending_choice_data
    logger.debug(f"Received PLAYER_CHOICE_MADE: {data}")
    input_mode = "COMMAND"
    pending_choice_data = None # 선택 완료 후 데이터 초기화


async def main():
    installer = GameManager()
    start_result = installer.start_game()
    if start_result is None:
        logger.error("게임을 시작하지 못했습니다.")
        exit(1)
        
    model, view, presenter = start_result

    installer.bus.subscribe(game_events.REQUEST_PLAYER_CHOICE, handle_request_player_choice)

    parser = CommandParser(presenter)

    # 시나리오 선택 로직
    scenario_loaded = False
    while not scenario_loaded:
        # ... (시나리오 선택 입력 및 installer.load_scenario 호출) ...
        print("\n=== 시나리오 선택 ===")
        print("1. 기본 시나리오 로드")
        user_input = input("시나리오를 선택하세요: ").strip()
        if user_input.lower() == '1':
            scenario_file = "data/scenarios/main_scenario.json"
            installer.load_scenario(scenario_file)
            logger.info("기본 시나리오가 로드되었습니다.")
            scenario_loaded = True
        else:
             logger.error("시나리오 로드 실패.")
             exit(1) # 또는 다른 처리
             
    # ⭐️ 초기 기반 배치 시작 요청 (시나리오 로딩 성공 후)
    if presenter.scenario is None:
        logger.error("시나리오가 설정되지 않았습니다. 초기 기반 배치를 시작할 수 없습니다.")
        exit(1)
    presenter.start_initial_base_placement(presenter.scenario) # presenter가 scenario 객체를 가지고 있다고 가정

    logger.info("Entering main game loop...")
    while True:
        try:
            # --- 상태에 따른 입력 처리 분기 ---
            if input_mode == "COMMAND":
                # === 일반 명령 입력 상태 ===
                current_player_id = model.get_current_player()
                if current_player_id is None: # 게임 시작 전이나 종료 후 처리
                     # logger.warning("Current player is not set.")
                     # break # 또는 다른 로직
                     prompt = f"{Fore.YELLOW}명령> {Style.RESET_ALL}" # 예외 처리
                else:
                     prompt = f"{Fore.GREEN}{Style.BRIGHT}[{current_player_id}] 명령> {Style.RESET_ALL}"

                user_input = input(prompt)

                if user_input.lower() in ('quit', 'exit'):
                    logger.info("Exiting game.")
                    break

                # ⭐️ 입력을 CommandParser에게 넘김
                parser.parse_command(user_input, current_player_id)

            elif input_mode == "CHOICE":
                # === 특정 선택 입력 상태 ===
                if pending_choice_data:
                    options = pending_choice_data.get("options", [])
                    context = pending_choice_data.get("context", {})
                    prompt_str = context.get("prompt") or "선택하세요:"

                    # ⭐️ CliView 대신 main.py에서 직접 질문 출력
                    print(f"\n🤔 {prompt_str} ({context.get('action', 'N/A')} for {context.get('party', 'N/A')})")
                    for i, option in enumerate(options):
                        # TODO: localize 함수 사용 필요 (CliView의 localize 가져오기)
                        print(f"  {i+1}. {option}")

                    choice_str = input("번호 입력> ").strip()
                    try:
                        choice_index = int(choice_str) - 1
                        if 0 <= choice_index < len(options):
                            selected_option = options[choice_index]
                            logger.debug(f"Player chose: {selected_option}")

                            # ⭐️ 선택 완료 이벤트를 발행 (Presenter가 들음)
                            installer.bus.publish(
                                game_events.PLAYER_CHOICE_MADE,
                                {"selected_option": selected_option, "context": context}
                            )
                            # ⭐️ 중요: 이벤트 발행 후 즉시 모드 변경 및 데이터 초기화
                            input_mode = "COMMAND"
                            pending_choice_data = None
                        else:
                            print(f"{Fore.RED}[ERROR]{Fore.RESET} 1부터 {len(options)} 사이의 번호를 입력하세요.")
                    except ValueError:
                        print(f"{Fore.RED}[ERROR]{Fore.RESET} 숫자를 입력하세요.")
                    except Exception as e:
                         logger.error(f"Error during player choice input: {e}")
                         # 에러 발생 시 모드 복구 고려
                         input_mode = "COMMAND"
                         pending_choice_data = None
                else:
                    logger.warning("Input mode is CHOICE, but no pending choice data found. Reverting to COMMAND mode.")
                    input_mode = "COMMAND" # 예외 처리

        except EOFError:
            logger.info("Exiting game (EOF).")
            break
        except KeyboardInterrupt:
            logger.info("Exiting game (Interrupt).")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")