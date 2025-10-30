



from typing import Optional
from game_action import Move, ActionTypeEnum, PlayOptionEnum
from enums import PartyID

class CommandParser:
    def __init__(self, presenter=None):
        self.presenter = presenter

    def parse_command_to_move(self, raw_input: str, player_id: PartyID) -> Optional[Move]:
        """
        입력 문자열을 분석하여 해당하는 Move 객체를 생성해 반환
        """
        cmd = raw_input.strip().lower()
        parts = cmd.split()

        if not parts:
            return None
        
        if parts[0] == 'play' and len(parts) >= 3:
            card_id = parts[1]
            try:
                play_option = PlayOptionEnum(parts[2].upper())
            except ValueError:
                return None # 잘못된 옵션

            card_action_type = None
            target_city = None

            if play_option == PlayOptionEnum.ACTION and len(parts) >= 4:
                # "play card01 action coup berlin"
                try:
                    card_action_type = ActionTypeEnum(parts[3].upper())
                    if len(parts) == 5:
                        target_city = parts[4]
                except ValueError:
                     return None
            
            return Move(
                player_id=player_id,
                action_type=ActionTypeEnum.PLAY_CARD,
                card_id=card_id,
                play_option=play_option,
                card_action_type=card_action_type,
                target_city=target_city
            )
        


        
        return None