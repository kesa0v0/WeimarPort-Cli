# console_agent.py
import asyncio # 기본 async 라이브러리
from typing import Any, List, Dict
from colorama import Fore, Style # 색상 사용 예시
from player_agent import IPlayerAgent
from models import GameModel
from enums import PartyID

class ConsoleAgent(IPlayerAgent):

    async def get_next_command(self, game_model: GameModel) -> str:
        # main.py의 메인 루프 입력 로직을 여기로 가져옴
        prompt = f"{Fore.GREEN}{Style.BRIGHT}[{self.party_id}] 명령> {Style.RESET_ALL}"
        # input()은 블로킹 함수이므로, asyncio 환경에서는 주의 필요
        # 여기서는 간단히 await asyncio.get_running_loop().run_in_executor(None, input, prompt) 사용 가능
        # 또는 더 간단하게 그냥 input 사용 (다른 Agent가 계산하는 동안 블로킹됨)
        command = await asyncio.to_thread(input, prompt) # input을 비동기처럼 실행
        return command.strip()

    async def get_choice(self, options: List[Any], context: Dict[str, Any]) -> Any:
        # main.py의 handle_request_player_choice 로직을 여기로 가져옴
        prompt_str = context.get("prompt") or f"[{self.party_id}] 선택하세요:"
        print(f"\n🤔 {prompt_str}")
        # TODO: localize 함수 사용
        localized_options = [str(opt) for opt in options] # 임시
        for i, option_str in enumerate(localized_options):
            print(f"  {i+1}. {option_str}")

        while True:
            choice_str = await asyncio.to_thread(input, "번호 입력> ")
            try:
                choice_index = int(choice_str) - 1
                if 0 <= choice_index < len(options):
                    return options[choice_index] # 선택된 원본 옵션 반환
                else:
                    print(f"{Fore.RED}[ERROR]{Fore.RESET} 1부터 {len(options)} 사이의 번호를 입력하세요.")
            except ValueError:
                print(f"{Fore.RED}[ERROR]{Fore.RESET} 숫자를 입력하세요.")

    def receive_message(self, event_type: str, data: Dict[str, Any]):
        # CliView의 on_show_message, on_show_error 등의 로직을 여기로 통합 가능
        # 또는 CliView는 공용 로그만, Agent는 개인 메시지만 처리하도록 분리 가능
        message = data.get("message") or data.get("error")
        if message:
             prefix = "[MSG]" if event_type == "UI_SHOW_MESSAGE" else "[ERR]"
             # 특정 플레이어에게만 보여야 하는 메시지인지 확인하는 로직 추가 가능
             print(f"{prefix} ({self.party_id}): {message}")
        elif event_type == "UI_SHOW_STATUS":
             # 상태 표시는 모든 플레이어에게 공통일 수 있으므로 별도 처리 또는 CliView 유지
             pass # 예시: 상태 메세지는 무시