
from typing import Dict


class Localizer:
    def __init__(self, translations: Dict[str, Dict[str, str]], default_language: str = "en"):
        self.translations = translations
        self.default_language = default_language

    def translate(self, key: str, language: str) -> str:
        if language in self.translations and key in self.translations[language]:
            return self.translations[language][key]
        elif key in self.translations.get(self.default_language, {}):
            return self.translations[self.default_language][key]
        else:
            return key  # Fallback to key if no translation found
        

        