from telethon.sync import TelegramClient
import os

# Путь к tdata директории
tdata_path = 'C:/Users/Гордей/Downloads/abc'

# Путь к файлу .session
session_file = 'D:/sessions'

# Убедитесь, что tdata существует
if not os.path.exists(tdata_path):
    print(f"tdata directory not found: {tdata_path}")
    exit(1)

# Подключаемся с помощью Telethon
client = TelegramClient(session_file, api_id=25754925, api_hash="13a6a7e363dc19f1312da11b9ed22f78")

# Открываем клиент с данными из tdata
client.session.tdata_path = tdata_path

# Пробуем подключиться
async def main():
    await client.connect()
    if not await client.is_user_authorized():
        print("User not authorized, please log in.")
    else:
        print("Successfully logged in!")

client.loop.run_until_complete(main())
