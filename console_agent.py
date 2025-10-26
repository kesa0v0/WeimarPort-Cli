# console_agent.py
import asyncio # 기본 async 라이브러리
from typing import Any, List, Dict
from colorama import Fore, Style # 색상 사용 예시
from player_agent import IPlayerAgent
from models import GameModel
from enums import PartyID

class ConsoleAgent(IPlayerAgent):
    def localize(self, text): # Temporary localization function
        temp_dict = {
            PartyID.KPD: "KPD",
            PartyID.SPD: "SPD",
            PartyID.ZENTRUM: "Zentrum",
            PartyID.DNVP: "DNVP",
        }

        if text in temp_dict:
            return temp_dict[text]

        return text  # Placeholder for localization logic

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
        if event_type == "UI_SHOW_MESSAGE":
            message = data.get("message")
            if message:
                print(f"{Fore.CYAN}[MSG] ({self.party_id}): {message}{Style.RESET_ALL}")
        elif event_type == "UI_SHOW_ERROR":
            error = data.get("error")
            if error:
                print(f"{Fore.RED}[ERR] ({self.party_id}): {error}{Style.RESET_ALL}")
        elif event_type == "UI_SHOW_STATUS":
            status_message = Fore.GREEN + Style.BRIGHT + "=== Game Status ===\n"
            status_message += Fore.CYAN + f"Round: {data['round']}\n"
            status_message += Fore.CYAN + f"Turn: {self.localize(data['turn'])}\n"
            status_message += Fore.YELLOW + "Parties:\n"
            for party_id, party_data in data['parties'].items():
                status_message += Fore.YELLOW + f" - {self.localize(party_id)}: {party_data.current_vp} VP, "
                status_message += Fore.YELLOW + f"{len(party_data.hand_timeline)} Timeline Cards, "
                status_message += Fore.YELLOW + f"{len(party_data.hand_party)} Party Cards\n"
                status_message += Fore.WHITE + f"  ↳ Units in Supply: {', '.join(party_data.unit_supply) if party_data.unit_supply else 'None'}\n"
            status_message += Fore.MAGENTA + "Cities:\n"
            for city_id, city_data in data['cities'].items():
                bases = ', '.join([f"{self.localize(party)}:{count}" for party, count in city_data.party_bases.items() if count > 0]) or "No bases"
                units = ', '.join(city_data.units_on_city) or "No units"
                threats = ', '.join(city_data.threats_on_city) or "No threats"
                city_status = f"Bases: {bases} | Units: {units} | Threats: {threats}"
                status_message += Fore.MAGENTA + f" - {self.localize(city_id)}: {city_status}\n"
            status_message += Fore.RED + "===================\n"
            print(status_message)