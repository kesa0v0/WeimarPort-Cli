# console_agent.py
import asyncio # 기본 async 라이브러리
from typing import Any, List, Dict
from colorama import Fore, Style # 색상 사용 예시
from game_action import Move
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

    async def get_next_move(self, game_model: GameModel) -> 'Move':
           from command_parser import CommandParser
           parser = CommandParser(None)  # presenter는 필요 없으므로 None

           while True:
               prompt = f"{Fore.GREEN}{Style.BRIGHT}[{self.localize(self.party_id)}] 명령 입력> {Style.RESET_ALL}"
               cmd_str = await asyncio.to_thread(input, prompt)
               
               move = parser.parse_command_to_move(cmd_str.strip(), self.party_id)
               
               if move:
                   return move
               else:
                   print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} 알 수 없는 명령입니다. 다시 입력해주세요.")

    async def get_choice(self, options: List[Any], context: Dict[str, Any]) -> Any:
            # main.py의 handle_request_player_choice 로직을 여기로 가져옴
            party_name = self.localize(self.party_id)
            prompt_str = context.get("prompt") or f"[{party_name}] 선택하세요:"
            print(f"\n🤔 [{party_name}] {prompt_str}")
            # TODO: localize 함수 사용
            localized_options = [str(opt) for opt in options] # 임시
            for i, option_str in enumerate(localized_options):
                print(f"  {i+1}. {option_str}")

            while True:
                choice_str = await asyncio.to_thread(input, f"[{party_name}] 번호 입력> ")
                try:
                    choice_index = int(choice_str) - 1
                    if 0 <= choice_index < len(options):
                        return options[choice_index] # 선택된 원본 옵션 반환
                    else:
                        print(f"{Fore.RED}[ERROR]{Fore.RESET} 1부터 {len(options)} 사이의 번호를 입력하세요.")
                except ValueError:
                    print(f"{Fore.RED}[ERROR]{Fore.RESET} 숫자를 입력하세요.")

    def receive_message(self, event_type: str, data: Dict[str, Any]):
        party_name = self.localize(self.party_id)
        if event_type == "UI_SHOW_MESSAGE":
            message = data.get("message")
            if message:
                print(f"{Fore.CYAN}[MSG] [{party_name}]: {message}{Style.RESET_ALL}")
        elif event_type == "UI_SHOW_ERROR":
            error = data.get("error")
            if error:
                print(f"{Fore.RED}[ERR] [{party_name}]: {error}{Style.RESET_ALL}")
        elif event_type == "UI_SHOW_STATUS":
            status_message = Fore.GREEN + Style.BRIGHT + f"=== Game Status ({party_name}) ===\n"
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