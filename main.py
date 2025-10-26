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
    # --- 시스템 조립 ---
    installer = GameManager()
    start_result = installer.start_game()
    if start_result is None:
        logger.error("게임을 시작하지 못했습니다.")
        exit(1)
        
    model, presenter = start_result

    # --- 에이전트 할당 ---
    agents = {
        PartyID.SPD: ConsoleAgent(PartyID.SPD),
        PartyID.ZENTRUM: RandomAIAgent(PartyID.ZENTRUM), # 예시: Zentrum은 AI
        PartyID.KPD: ConsoleAgent(PartyID.KPD),       # 예시: KPD는 사람
        PartyID.DNVP: RandomAIAgent(PartyID.DNVP),  # 예시: DNVP는 AI
    }
    logger.info(f"Player agents assigned: { {pid.name: type(agent).__name__ for pid, agent in agents.items()} }")

    # --- EventBus <-> Agent 연결 (메시지 수신용) ---
    # Presenter가 발행하는 UI 이벤트를 각 Agent가 받도록 구독 설정
    def message_router(event_type, data):
         # TODO: 모든 agent에게 보낼지, 특정 agent에게 보낼지 결정하는 로직
         # data 딕셔너리에 'target_party_id' 같은 필드를 추가하는 것을 고려
         target_party_id_str = data.get("target_party_id")
         if target_party_id_str:
              target_party_id = PartyID(target_party_id_str)
              if target_party_id in agents:
                   agents[target_party_id].receive_message(event_type, data)
         else: # 타겟 없으면 모두에게 브로드캐스트 (예: 상태 변경)
              for agent in agents.values():
                   agent.receive_message(event_type, data)

    # installer.bus.subscribe(game_events.REQUEST_PLAYER_CHOICE, handle_request_player_choice)
    installer.bus.subscribe(game_events.UI_SHOW_MESSAGE, lambda data: message_router("UI_SHOW_MESSAGE", data))
    installer.bus.subscribe(game_events.UI_SHOW_ERROR, lambda data: message_router("UI_SHOW_ERROR", data))
    installer.bus.subscribe(game_events.UI_SHOW_STATUS, lambda data: message_router("UI_SHOW_STATUS", data))
    # 주의: 위 방식은 모든 UI 이벤트에 대해 라우터를 호출. 더 세분화된 구독 필요할 수 있음.


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

    parser = CommandParser(presenter)
    logger.info("Entering main game loop...")
    while True:
        try:
            current_player_id = model.get_current_player()
            if not current_player_id:
                 logger.warning("Waiting for game to start or player to be set...")
                 await asyncio.sleep(0.1) # 플레이어 설정될 때까지 대기
                 continue

            current_agent = agents[current_player_id]

            # ⭐️ 에이전트로부터 다음 명령어 비동기적으로 받기
            command_str = await current_agent.get_next_command(model)

            if command_str.lower() in ('quit', 'exit'):
                logger.info("Exit command received.")
                break

            # ⭐️ 명령어를 파서에게 넘겨 Presenter 호출
            parser.parse_command(command_str, current_player_id)

            # TODO: 게임 종료 조건 확인 로직 추가

            # ⭐️ 중요: Presenter가 Model을 변경하고 이벤트를 발행하면,
            # Agent의 receive_message가 호출되어 출력/로깅이 이루어짐.
            # 선택 요청(REQUEST_PLAYER_CHOICE)이 발행되면 Presenter가
            # await relevant_agent.get_choice(...) 를 호출하여 응답을 받음.

        except Exception as e: # 예외 처리 강화
             logger.exception(f"Error in main loop: {e}")
             # 또는 break 등 에러 처리

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")