import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Твои данные из главного экрана Twilio (которые были на твоем первом скриншоте)
# Прямо здесь в коде вставим их для быстрого теста
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Номера телефонов
TWILIO_NUMBER = "+12513222367"  # Твой купленный номер Twilio
MY_NUMBER = "+77075525529"  # ВПИШИ СЮДА СВОЙ КАЗАХСТАНСКИЙ МОБИЛЬНЫЙ НОМЕР

# Ссылка на твой работающий LocalTunnel сервер
WEBHOOK_URL = "https://cruel-pears-trade.loca.lt/twiml"


def make_test_call():
    print(f"🚀 Инициирую бесплатный вызов с {TWILIO_NUMBER} на {MY_NUMBER}...")

    # Подключаемся к клиенту Twilio SDK
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # Создаем исходящий звонок, который перенаправит поток на наш FastAPI
    call = client.calls.create(
        to=MY_NUMBER,
        from_=TWILIO_NUMBER,
        url=WEBHOOK_URL
    )

    print(f"✅ Звонок успешно запущен! ID звонка: {call.sid}")
    print("📱 Проверяй свой мобильный телефон, он должен зазвонить!")


if __name__ == "__main__":
    make_test_call()
