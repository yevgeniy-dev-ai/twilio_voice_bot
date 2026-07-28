import asyncio
import json
import base64
import os
import websockets

# Адрес локального запущенного FastAPI сервера
WS_URL = "ws://127.0.0.1:8000/media-stream"
TEST_FILE = "test.wav"


async def simulate_twilio_call():
    # Проверяем наличие тестового аудиофайла в папке перед запуском
    if not os.path.exists(TEST_FILE):
        print(f"❌ Ошибка: Файл '{TEST_FILE}' не найден в текущей папке!")
        print("Пожалуйста, скопируй любой рабочий .wav файл в эту папку и назови его 'test.wav'")
        return

    print(f"🔌 Подключаюсь к WebSocket бота: {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Соединение открыто! Симулирую старт телефонного звонка...")

            # 1. Отправляем стартовый пакет по протоколу Twilio Media Streams
            start_packet = {
                "event": "start",
                "start": {
                    "streamSid": "MZ_TEST_STREAM_12345",
                    "callSid": "CA_TEST_CALL_12345"
                }
            }
            await websocket.send(json.dumps(start_packet))
            await asyncio.sleep(0.5)

            print(f"🎤 Читаю реальный файл '{TEST_FILE}' и стримлю его аудио-байты в сокет...")
            # Читаем реальные бинарные данные звука с диска
            with open(TEST_FILE, "rb") as f:
                wav_data = f.read()

            # Кодируем байты в строку Base64 для передачи внутри JSON пакета
            base64_payload = base64.b64encode(wav_data).decode('utf-8')

            media_packet = {
                "event": "media",
                "media": {
                    "payload": base64_payload
                }
            }
            await websocket.send(json.dumps(media_packet))
            print("📥 Аудио-байты фразы успешно отправлены в буфер. Ждем реакцию ИИ...")

            # 2. Переходим в асинхронный режим ожидания ответа от ИИ-помощника
            try:
                print("⏳ Слушаю обратный канал связи WebSocket...")
                while True:
                    response = await websocket.recv()
                    packet = json.loads(response)

                    if packet.get('event') == 'media':
                        print("\n" + "=" * 60)
                        print("🔥 ПОЛУЧЕН ОТВЕТ ОТ БОТА!")
                        print("🤖 ИИ успешно сгенерировал и стримит аудио-байты Роджера обратно в трубку!")
                        print("=" * 60 + "\n")
                        break
            except asyncio.TimeoutError:
                print("⏳ ИИ слишком долго обрабатывает запрос...")

            # 3. Закрываем виртуальный звонок
            stop_packet = {"event": "stop"}
            await websocket.send(json.dumps(stop_packet))
            print("🛑 Симуляция звонка завершена успешно. Сессия закрыта.")

    except Exception as e:
        print(f"❌ Ошибка подключения или передачи данных: {e}")


if __name__ == "__main__":
    # Запуск асинхронного клиента
    asyncio.run(simulate_twilio_call())
