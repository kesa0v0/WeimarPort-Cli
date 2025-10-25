import logging
from colorama import init as init_colorama, Fore, Style

from enums import PartyID
from event_bus import EventBus
from game_events import UI_SHOW_STATUS

logger = logging.getLogger(__name__)
init_colorama(autoreset=True)

class CliView:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(UI_SHOW_STATUS, self.on_show_status)
    
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

    def print(self, message):
        print(message)
