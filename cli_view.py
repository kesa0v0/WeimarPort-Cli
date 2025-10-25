import logging
from colorama import init as init_colorama, Fore, Style

from enums import PartyID
from event_bus import EventBus
from game_events import UI_SHOW_STATUS
import game_events

logger = logging.getLogger(__name__)
init_colorama(autoreset=True)

class CliView:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(UI_SHOW_STATUS, self.on_show_status)
        self.bus.subscribe(game_events.REQUEST_PLAYER_CHOICE, self.on_request_choice)
    
    def localize(self, text):
        temp_dict = {
            PartyID.KPD: "KPD",
            PartyID.SPD: "SPD",
            PartyID.ZENTRUM: "Zentrum",
            PartyID.DNVP: "DNVP",
        }

        if text in temp_dict:
            return temp_dict[text]

        return text  # Placeholder for localization logic

    def on_show_status(self, data):
        status_message = Fore.GREEN + Style.BRIGHT + "=== Game Status ===\n"
        
        status_message += Fore.CYAN + f"Round: {data['round']}\n"
        status_message += Fore.CYAN + f"Turn: {data['turn']}\n"

        status_message += Fore.YELLOW + "Parties:\n"
        for party_id, party_data in data['parties'].items():
            status_message += Fore.YELLOW + f" - {self.localize(party_id)}: {party_data.current_vp} VP, "
            status_message += Fore.YELLOW + f"{len(party_data.hand_timeline)} Timeline Cards, "
            status_message += Fore.YELLOW + f"{len(party_data.hand_party)} Party Cards\n"
            status_message += Fore.WHITE + f"  ↳ Units in Supply: {', '.join(party_data.unit_supply) if party_data.unit_supply else 'None'}\n"
            

        status_message += Fore.MAGENTA + "Cities:\n"
        for city_id, city_data in data['cities'].items():
            bases = ', '.join([f"{party.name}:{count}" for party, count in city_data.party_bases.items() if count > 0]) or "No bases"
            units = ', '.join(city_data.units_on_city) or "No units"
            threats = ', '.join(city_data.threats_on_city) or "No threats"
            city_status = f"Bases: {bases} | Units: {units} | Threats: {threats}"
            status_message += Fore.MAGENTA + f" - {self.localize(city_id)}: {city_status}\n"
        status_message += Fore.RED + "===================\n"
        self.print(status_message)

    def on_request_choice(self, data):
        """선택 요청을 받아 사용자에게 보여주고 입력을 받습니다."""
        prompt = data.get("prompt", "선택하세요:")
        options = data.get("options", [])
        context = data.get("context", {}) # 선택에 필요한 추가 정보 (예: 어느 액션 중인지)

        print(f"\n🤔 {prompt}")
        for i, option in enumerate(options):
            # 옵션을 사용자 친화적으로 표시 (예: PartyID Enum -> 정당 이름)
            print(f"  {i+1}. {self.localize(option)}") # localize 함수 필요

        while True:
            try:
                choice_str = input("번호 입력> ")
                choice_index = int(choice_str) - 1
                if 0 <= choice_index < len(options):
                    selected_option = options[choice_index]
                    logger.debug(f"Player chose: {selected_option}")

                    # ⭐️ 선택 완료 이벤트를 발행 (선택 결과와 원래 context 포함)
                    self.bus.publish(game_events.PLAYER_CHOICE_MADE, {
                        "selected_option": selected_option,
                        "context": context # 원래 요청의 context를 그대로 돌려줌
                    })
                    break
                else:
                    print(f"{Fore.RED}[ERROR]{Fore.RESET} 1부터 {len(options)} 사이의 번호를 입력하세요.")
            except ValueError:
                print(f"{Fore.RED}[ERROR]{Fore.RESET} 숫자를 입력하세요.")
            except Exception as e:
                 logger.error(f"Error during player choice input: {e}")
                 # 에러 발생 시 처리 (예: 선택 취소 이벤트 발행)
                 break

    def print(self, message):
        print(message)
