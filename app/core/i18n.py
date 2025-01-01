# app/core/i18n.py
from typing import Callable, Dict
from functools import lru_cache
import json
from pathlib import Path

class I18nProvider:
    """Provides Arabic/English internationalization support"""
    
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = 'en'
        self.supported_languages = {'en', 'ar'}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load Arabic and English translations from the translations directory"""
        translations_dir = Path(__file__).parent / 'translations'        
        if not translations_dir.exists():
            raise FileNotFoundError(f"Translations directory not found: {translations_dir}")

        # Only load ar and en translations
        for lang in self.supported_languages:
            file_path = translations_dir / f'{lang}.json'
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[lang] = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in translation file {file_path}: {str(e)}")
            except Exception as e:
                raise Exception(f"Error loading translation file {file_path}: {str(e)}")

    def get_translation(self, language: str = 'en') -> Callable[[str], str]:
        """Get translation function for Arabic or English"""
        # Default to English if unsupported language is requested
        if language not in self.supported_languages:
            language = self.default_language
            
        translations = self.translations.get(language, self.translations[self.default_language])
        
        def translate(key: str, **kwargs) -> str:
            # Get translation or fallback to default language or key itself
            translation = translations.get(key)
            
            if translation is None:
                # Try default language if translation not found
                translation = self.translations[self.default_language].get(key, key)
            
            # Apply any format arguments
            if kwargs:
                try:
                    return translation.format(**kwargs)
                except KeyError as e:
                    return translation
            
            return translation
            
        return translate

# Singleton instance
i18n_provider = I18nProvider()

@lru_cache(maxsize=128)
def get_translation(language: str = 'en') -> Callable[[str], str]:
    """Get cached translation function for Arabic or English"""
    return i18n_provider.get_translation(language)