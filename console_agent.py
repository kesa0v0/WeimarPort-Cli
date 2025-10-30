# console_agent.py
import asyncio # 기본 async 라이브러리
from typing import Any, List, Dict
from colorama import Fore, Style # 색상 사용 예시
from game_action import ActionTypeEnum, Move, PlayOptionEnum
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
        while True:
            # 1. 주 행동 선택
            main_actions = ["Play Card", "Inspect"]
            chosen_action = await self.get_choice(main_actions, {"prompt": "무엇을 하시겠습니까?"})

            if chosen_action == "Play Card":
                # 2. 카드 선택
                player_hand = game_model.party_states[self.party_id].hand_party
                if not player_hand:
                    print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} 손에 카드가 없습니다.")
                    continue

                chosen_card = await self.get_choice(player_hand, {"prompt": "어떤 카드를 사용하시겠습니까?"})

                # 3. 플레이 옵션 선택
                play_options = [PlayOptionEnum.EVENT, PlayOptionEnum.DEBATE, PlayOptionEnum.ACTION]
                chosen_play_option = await self.get_choice(play_options, {"prompt": f"'{chosen_card}'를 어떻게 사용하시겠습니까?"})

                card_action_type = None
                target_city = None

                if chosen_play_option == PlayOptionEnum.ACTION:
                    # 4. 카드 액션 타입 선택 (임시)
                    # TODO: 카드 데이터에서 실제 가능한 액션을 가져와야 함
                    action_types = ActionTypeEnum.__members__.values()
                    chosen_card_action = await self.get_choice(action_types, {"prompt": "어떤 액션을 하시겠습니까?"})
                    card_action_type = chosen_card_action

                    # 5. 대상 도시 선택 (액션에 따라 필요할 경우)
                    # TODO: 모든 액션에 도시가 필요한 것은 아님. 조건부로 질문해야 함.
                    if card_action_type in [ActionTypeEnum.COUP, ActionTypeEnum.DEMONSTRATION]:
                        cities = list(game_model.cities_state.keys())
                        target_city = await self.get_choice(cities, {"prompt": "어느 도시에서 실행하시겠습니까?"})

                return Move(
                    player_id=self.party_id,
                    card_action_type=card_action_type,
                    card_id=chosen_card,
                    play_option=chosen_play_option,
                    target_city=target_city
                )

            elif chosen_action == "Inspect":
                status_data = {
                    "round": game_model.round,
                    "turn": game_model.turn,
                    "parties": game_model.party_states,
                    "cities": game_model.cities_state,
                }
                self.receive_message("UI_SHOW_STATUS", status_data)
                continue


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