import os
import json
import base64
import asyncio
import logging
import audioop
import wave
import io
from fastapi import FastAPI, Response, WebSocket
from dotenv import load_dotenv
from voice_bot_basic import VoiceBotBasic

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
ai_core = VoiceBotBasic()

# Глобальный буфер памяти диалога для этого звонка
conversation_history = []
SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты — лаконичный телефонный ассистент. Отвечай строго на русском языке, очень кратко (1-2 коротких предложения)."
}


def convert_mulaw_to_wav(mulaw_data):
    """Конвертирует телефонный формат Mulaw 8kHz в стандартный WAV PCM 16kHz для Whisper"""
    # 1. Декодируем Mulaw байты в линейный PCM (16-bit)
    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
    # 2. Повышаем частоту дискретизации (resample) с 8000 Гц до 16000 Гц
    pcm_16k, _ = audioop.ratecv(pcm_data, 2, 1, 8000, 16000, None)

    # 3. Упаковываем сырые байты в контейнер WAV в оперативной памяти (без записи на диск)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(pcm_16k)

    return wav_buffer.getvalue()


@app.post("/twiml")
async def route_twilio_call():
    """Инструкция для Twilio при входящем вызове"""
    logger.info("📞 Входящий звонок соединен. Включаю аудиострим...")
    host = "cruel-pears-trade.loca.lt"  # Твой текущий домен LocalTunnel

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="wss://{host}/media-stream" />
        </Connect>
    </Response>
    """
    return Response(content=twiml_response, media_type="text/xml")


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """WebSocket-обработчик стрима звонка в реальном времени"""
    await websocket.accept()
    logger.info("🔌 WebSocket-аудиострим с Twilio успешно открыт!")

    audio_buffer = bytearray()
    stream_sid = None  # Идентификатор стрима для отправки звука обратно

    # Сбрасываем контекст для нового звонка
    global conversation_history
    conversation_history = [SYSTEM_PROMPT]

    try:
        while True:
            data = await websocket.receive_text()
            packet = json.loads(data)

            if packet['event'] == 'start':
                stream_sid = packet['start']['streamSid']
                logger.info(f"🚀 Стрим запущен. StreamSID: {stream_sid}")

            elif packet['event'] == 'media':
                # Извлекаем входящие чанки голоса клиента
                media = packet['media']
                payload = base64.b64decode(media['payload'])
                audio_buffer.extend(payload)

                # Симулируем детектор конца фразы (VAD): если накопили ~4.5 секунды звука
                if len(audio_buffer) > 36000:
                    logger.info("🧠 Клиент закончил говорить. Запуск ИИ-пайплайна...")

                    # 1. Конвертируем накопленный Mulaw-поток в WAV байты
                    raw_mulaw = bytes(audio_buffer)
                    audio_buffer.clear()  # Очищаем буфер для следующей фразы клиента

                    wav_bytes = convert_mulaw_to_wav(raw_mulaw)

                    # Сохраняем временный файл для Whisper
                    temp_wav = "temp_voice.wav"
                    with open(temp_wav, "wb") as f:
                        f.write(wav_bytes)

                    # 2. Вызываем Whisper (ASR) в отдельном потоке
                    loop = asyncio.get_running_loop()
                    user_text = await loop.run_in_executor(None, ai_core.asr_recognize_speech, temp_wav)

                    if os.path.exists(temp_wav):
                        os.remove(temp_wav)

                    if not user_text.strip():
                        logger.info("🤫 В буфере тишина или шум, пропускаем.")
                        continue

                    # 3. Добавляем в историю и вызываем Groq (LLM)
                    conversation_history.append({"role": "user", "content": user_text})

                    chat_completion = await loop.run_in_executor(
                        None,
                        lambda: ai_core.groq_client.chat.completions.create(
                            messages=conversation_history,
                            model="llama-3.3-70b-versatile",
                            max_tokens=100
                        )
                    )
                    bot_response = chat_completion.choices[0].message.content.strip()
                    conversation_history.append({"role": "assistant", "content": bot_response})
                    logger.info(f"🤖 Ответ ИИ: {bot_response}")

                    # 4. Генерируем аудиоответ в ElevenLabs (TTS)
                    temp_mp3 = "temp_out.mp3"
                    await loop.run_in_executor(None, ai_core.tts_synthesize_speech, bot_response, temp_mp3)

                    # 5. Читаем сгенерированный MP3, переводим в телефонный формат Mulaw и отправляем в трубку
                    if os.path.exists(temp_mp3):
                        # С помощью ffmpeg перегоняем MP3 в сырой Mulaw 8kHz для Twilio
                        process = await asyncio.create_subprocess_exec(
                            'ffmpeg', '-y', '-i', temp_mp3, '-f', 'mulaw', '-ar', '8000', '-ac', '1', 'temp_phone.raw',
                            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                        )
                        await process.wait()

                        if os.path.exists('temp_phone.raw'):
                            with open('temp_phone.raw', 'rb') as raw_f:
                                reply_bytes = raw_f.read()

                            # Нарезаем аудиоответ на маленькие пакеты и отправляем в WebSocket Twilio
                            chunk_size = 3200
                            for i in range(0, len(reply_bytes), chunk_size):
                                audio_chunk = reply_bytes[i:i + chunk_size]
                                base64_audio = base64.b64encode(audio_chunk).decode('utf-8')

                                # Формируем JSON-пакет по протоколу Twilio Media Streams
                                response_packet = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": base64_audio
                                    }
                                }
                                await websocket.send_text(json.dumps(response_packet))
                                await asyncio.sleep(0.02)  # Имитируем реальное время трансляции

                            os.remove('temp_phone.raw')
                        os.remove(temp_mp3)

            elif packet['event'] == 'stop':
                logger.info("🛑 Звонок завершен.")
                break

    except Exception as e:
        logger.error(f"❌ Ошибка в аудио-стриме: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
