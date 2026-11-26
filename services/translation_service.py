import urllib.request
import urllib.parse
import json


def translate_text(text: str, target_lang: str) -> dict:
    """Translate text to target language: en | ru | ur.

    Returns dict with translated text and language info.
    """
    if not text or not text.strip():
        return {"translated": text, "detected_lang": "en", "target_lang": target_lang}

    tgt = target_lang if target_lang in ["en", "ru", "ur"] else "en"

    # 1. Primary: Google Client GTX API (super fast, robust, no rate-limiting)
    try:
        params = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": tgt, "dt": "t", "q": text})
        url = f"https://translate.googleapis.com/translate_a/single?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            detected = data[2] if len(data) > 2 else "auto"

            # If detected language is already target language, auto-translate to English or Urdu
            if detected == tgt and tgt != "en":
                params_en = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text})
                req_en = urllib.request.Request(
                    f"https://translate.googleapis.com/translate_a/single?{params_en}",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req_en, timeout=6) as resp_en:
                    data_en = json.loads(resp_en.read().decode())
                    translated = "".join([part[0] for part in data_en[0] if part and part[0]])
                    tgt = "en"
            elif detected == tgt and tgt == "en":
                params_ur = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "ur", "dt": "t", "q": text})
                req_ur = urllib.request.Request(
                    f"https://translate.googleapis.com/translate_a/single?{params_ur}",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req_ur, timeout=6) as resp_ur:
                    data_ur = json.loads(resp_ur.read().decode())
                    translated = "".join([part[0] for part in data_ur[0] if part and part[0]])
                    tgt = "ur"

            return {"translated": translated or text, "detected_lang": detected, "target_lang": tgt}
    except Exception as e:
        print(f"[Google GTX Translation Error] {e}")

    # 2. Fallback: MyMemory Free Translation API
    try:
        params = urllib.parse.urlencode({"q": text, "langpair": f"autodetect|{tgt}"})
        url = f"https://api.mymemory.translated.net/get?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            translated = data.get("responseData", {}).get("translatedText")
            if translated:
                return {"translated": translated, "detected_lang": "auto", "target_lang": tgt}
    except Exception as e:
        print(f"[MyMemory Translation Error] {e}")

    return {"translated": text, "detected_lang": "auto", "target_lang": tgt}
