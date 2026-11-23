from deep_translator import GoogleTranslator

def translate_text(text: str, target_lang: str) -> str:
    """Translate text to target language. target_lang: en | ru | ur"""
    try:
        if not text or not text.strip():
            return text
        tgt = target_lang if target_lang in ["en", "ru", "ur"] else "en"
        result = GoogleTranslator(source="auto", target=tgt).translate(text)
        return result or text
    except Exception as e:
        print(f"[Translation Error] {e}")
        return text
