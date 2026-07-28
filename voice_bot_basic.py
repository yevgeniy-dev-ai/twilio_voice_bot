#!/usr/bin/env python3
"""
Voice Bot Basic - Проект 1 (с Groq)
ASR (распознавание) → LLM (обработка) → TTS (синтез)

Требуемые зависимости:
pip install openai-whisper groq elevenlabs python-dotenv
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import whisper
from groq import Groq
from elevenlabs.client import ElevenLabs

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузить переменные окружения
load_dotenv()

# Получить API ключи
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Проверка наличия ключей
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY не найден в .env")
if not ELEVENLABS_API_KEY:
    raise ValueError("❌ ELEVENLABS_API_KEY не найден в .env")

logger.info("✅ API ключи загружены успешно")


class VoiceBotBasic:
    """Простой голосовой бот: ASR → LLM → TTS"""

    def __init__(self):
        """Инициализация бота"""
        self.whisper_model = None
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        logger.info("🤖 VoiceBot инициализирован")

    def load_whisper_model(self):
        """Загрузить модель Whisper (скачается при первом запуске)"""
        if self.whisper_model is None:
            logger.info("📥 Загружаю модель Whisper (первый запуск может занять время)...")
            self.whisper_model = whisper.load_model("base")
            logger.info("✅ Модель Whisper загружена")
        return self.whisper_model

    def asr_recognize_speech(self, audio_path: str) -> str:
        """
        Шаг 1: Распознавание речи (ASR)
        Берёшь аудиофайл → получаешь текст
        """
        logger.info(f"🎤 Распознаю речь из файла: {audio_path}")

        # Проверка существования файла
        file_path = Path(audio_path)

        if not file_path.exists():
            raise FileNotFoundError(f"❌ Файл не найден: {file_path.absolute()}")

        # Загрузить модель
        model = self.load_whisper_model()

        # Распознать речь
        try:
            result = model.transcribe(str(file_path.absolute()), language="ru")
            text = result["text"].strip()
            logger.info(f"✅ Распознано: '{text}'")
            return text
        except Exception as e:
            logger.error(f"❌ Ошибка распознавания: {e}")
            raise

    def llm_process_text(self, user_text: str) -> str:
        """
        Шаг 2: Обработка текста LLM (Groq)
        Берёшь текст → отправляешь в Groq → получаешь ответ
        """
        logger.info(f"🧠 Обрабатываю текст в Groq: '{user_text}'")

        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": user_text,
                    }
                ],
                model="llama-3.3-70b-versatile",  # Бесплатный и быстрый
                max_tokens=200,
            )

            response_text = chat_completion.choices[0].message.content.strip()
            logger.info(f"✅ Ответ Groq: '{response_text}'")
            return response_text
        except Exception as e:
            logger.error(f"❌ Ошибка Groq API: {e}")
            raise

    def tts_synthesize_speech(self, text: str, output_path: str = "output.mp3"):
        """
        Шаг 3: Синтез речи (TTS)
        Автоматически находит доступный голос на вашем API-ключе и делает озвучку.
        """
        logger.info(f"🔊 Синтезирую речь: '{text}'")
        try:
            # 1. Запрашиваем список всех доступных голосов для вашего API-ключа
            logger.info("🔍 Запрашиваю список доступных голосов на вашем аккаунте...")
            voices_response = self.elevenlabs_client.voices.get_all()

            if not voices_response.voices:
                raise ValueError("❌ На вашем аккаунте ElevenLabs не найдено ни одного доступного голоса!")

            # Берём самый первый доступный голос из списка вашего профиля
            selected_voice = voices_response.voices[0]
            logger.info(f"🎤 Автоматически выбран голос: '{selected_voice.name}' (ID: {selected_voice.voice_id})")

            # 2. Синтезируем речь, используя динамически полученный ID
            audio = self.elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=selected_voice.voice_id,  # Передаем рабочий ID
                model_id="eleven_flash_v2_5"  # Самая быстрая модель
            )

            # 3. Сохраняем в файл
            with open(output_path, "wb") as f:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)

            logger.info(f"✅ Аудио успешно сохранено: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}")
            raise

    def process_audio(self, input_audio: str, output_audio: str = "output.mp3") -> dict:
        """
        Полный pipeline: Аудио → Текст → LLM → Текст → Аудио
        """
        logger.info(f"\n{'=' * 60}")
        logger.info("🚀 НАЧИНАЮ ПОЛНЫЙ PIPELINE")
        logger.info(f"{'=' * 60}\n")

        try:
            # Шаг 1: ASR - распознавание
            recognized_text = self.asr_recognize_speech(input_audio)

            # Шаг 2: LLM - обработка
            response_text = self.llm_process_text(recognized_text)

            # Шаг 3: TTS - синтез
            output_file = self.tts_synthesize_speech(response_text, output_audio)

            logger.info(f"\n{'=' * 60}")
            logger.info("✅ PIPELINE ЗАВЕРШЁН УСПЕШНО")
            logger.info(f"{'=' * 60}\n")

            return {
                "input_audio": input_audio,
                "recognized_text": recognized_text,
                "response_text": response_text,
                "output_audio": output_file,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"\n❌ ОШИБКА В PIPELINE: {e}\n")
            return {
                "status": "error",
                "error": str(e)
            }


def main():
    """Главная функция"""

    # Получить путь к аудиофайлу
    if len(sys.argv) < 2:
        print("\n📝 Использование:")
        print("  python voice_bot_basic.py <input_audio.wav>")
        print("\nПример:")
        print("  python voice_bot_basic.py test.wav")
        print("\nРезультат будет сохранён как: output.mp3\n")
        return

    input_file = sys.argv[1]

    # Создать бота
    bot = VoiceBotBasic()

    # Обработать аудио
    result = bot.process_audio(input_file)

    # Вывести результат
    if result["status"] == "success":
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ:")
        print("=" * 60)
        print(f"Входной файл:      {result['input_audio']}")
        print(f"Распознано:        {result['recognized_text']}")
        print(f"Ответ Groq:        {result['response_text']}")
        print(f"Выходной файл:     {result['output_audio']}")
        print("=" * 60 + "\n")
    else:
        print(f"\n❌ Ошибка: {result['error']}\n")


if __name__ == "__main__":
    main()