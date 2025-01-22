#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from datetime import datetime, timezone
from loguru import logger
from telethon import TelegramClient, events
from telethon.tl.types import Channel
import random
import g4f
from g4f.client import Client

async def connect_telegram_account(session_name, api_id, api_hash, proxy=None):
    """Подключение к аккаунту Telegram"""
    try:
        client = TelegramClient(session_name, api_id, api_hash, proxy=proxy)
        await client.connect()
        if not await client.is_user_authorized():
            raise ValueError("Telegram client is not authorized. Проверьте API ID и Hash.")
        return client
    except Exception as e:
        logger.exception("Ошибка подключения к Telegram.")
        raise

class TelegramCommentator:
    """Отправка комментариев в Telegram-каналы"""

    def __init__(self, client, mode):
        self.client = client
        self.mode = mode
        self.processed_messages = set()
        self.lock = asyncio.Semaphore(10)  # Ограничение параллельных запросов

    async def generate_comment(self, prompt: str) -> str:
        """Генерация комментария с использованием g4f"""
        try:
            def sync_generate():
                client = Client()
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    provider=g4f.Provider.Blackbox
                )
                if response and response.choices:
                    return response.choices[0].message.content.strip()
                else:
                    raise Exception("Ошибка генерации комментария.")

            return await asyncio.get_event_loop().run_in_executor(None, sync_generate)
        except Exception as e:
            logger.error(f"Ошибка генерации комментария: {e}")
            raise

    async def send_comment(self, channel_name, message):
        """Отправка комментария в канал."""
        async with self.lock:
            try:
                if message.id in self.processed_messages:
                    logger.info(f"Сообщение {message.id} уже обработано, пропуск.")
                    return

                # Получаем чат или канал
                channel = await self.client.get_entity(channel_name)

                # Проверяем, что это канал
                if not isinstance(channel, Channel):
                    logger.warning(f"Сообщение не отправлено, так как {channel_name} не является каналом.")
                    return

                prompt = (
                    f"Напиши комментарий до 20 слов, который будет провокационным и может вызвать реакцию. Используй ошибки в словах или логике, чтобы он звучал более естественно, например: 'Сейчас бы в 2025 веке спорить про это'. Если пост связан с политикой, войнами, военными действиями и подобное, то тогда напиши нейтральный комментарий, например: 'Наши бойцы России лучшие и они всех победят!': {message.raw_text}"
                )
                comment = await self.generate_comment(prompt)

                # Задержка перед отправкой комментария (случайное время от 10 до 15 секунд)
                delay_time = random.randint(3, 7)
                logger.info(f"Ждем {delay_time} секунд до отправки комментария в канал {channel_name}...")

                await asyncio.sleep(delay_time)

                sent_message = await self.client.send_message(entity=channel_name, message=comment, comment_to=message.id)
                logger.info(f"Комментарий отправлен в канал {channel_name}: {comment}")
                self.processed_messages.add(message.id)

                # Планируем изменение комментария через 4 секунды только в режиме 2
                if self.mode == 2:
                    asyncio.create_task(self.edit_comment_after_delay(sent_message, "ребят, кому нужен инвайт в шутер где за убитых монстров платят?", delay=300))
            except Exception as e:
                logger.error(f"Ошибка при отправке комментария в {channel_name}: {e}")

    async def edit_comment_after_delay(self, message, new_text, delay):
        """Редактирование комментария через заданное время."""
        try:
            await asyncio.sleep(delay)
            await self.client.edit_message(message, new_text)
            logger.info(f"Комментарий изменен на: {new_text}")
        except Exception as e:
            logger.error(f"Ошибка при редактировании комментария: {e}")

async def main():
    """Основная логика работы"""
    # Данные для подключения
    api_id_monitor = "20159927"
    api_hash_monitor = "7037638b49dd6735e11bbf84339d04ec"
    api_id_commentator = "25754925"
    api_hash_commentator = "13a6a7e363dc19f1312da11b9ed22f78"

    # Настройки прокси
    # proxy = {
    #     "proxy_type": "socks5",  # Тип прокси (SOCKS5)
    #     "addr": "103.82.103.137",  # Адрес прокси
    #     "port": 61145,  # Порт прокси
    #     "username": "pUVjDo3mPq",  # Логин прокси
    #     "password": "O5OhyPVOfU",  # Пароль прокси
    # }

    # client_monitor = await connect_telegram_account("accounts/monitor_account", api_id_monitor, api_hash_monitor, proxy)
    # client_commentator = await connect_telegram_account("accounts/commentator_account", api_id_commentator, api_hash_commentator, proxy)

    client_monitor = await connect_telegram_account("accounts/monitor_account", api_id_monitor, api_hash_monitor)
    client_commentator = await connect_telegram_account("accounts/commentator_account", api_id_commentator, api_hash_commentator)

    print("Выберите режим работы:")
    print("1. Нейрокомментинг")
    print("2. Комментирование с последующим редактированием")

    mode = int(input("Введите номер режима: "))

    if mode not in [1, 2]:
        logger.error("Неверный режим работы. Перезапустите программу и выберите 1 или 2.")
        return

    commentator = TelegramCommentator(client_commentator, mode)

    @client_monitor.on(events.NewMessage())
    async def handle_new_message(event):
        """Обработка новых сообщений"""
        try:
            channel = await event.get_chat()
            if not isinstance(channel, Channel):
                logger.warning("Получено сообщение не из канала. Игнорируем.")
                return  # Игнорируем неканальные сообщения

            channel_name = channel.username or channel.id
            message = event.message
            logger.info(f"Новое сообщение в {channel_name}: {message.raw_text[:30]}...")

            # Отправляем комментарий
            await commentator.send_comment(channel_name, message)
        except Exception as e:
            logger.error(f"Ошибка обработки нового сообщения: {e}")

    logger.info("Мониторинг новых сообщений запущен.")
    await client_monitor.run_until_disconnected()

if __name__ == "__main__":
    logger.add("log/log.log", rotation="1 MB", compression="zip")
    asyncio.run(main())




















# client_monitor = await connect_telegram_account("accounts/monitor_account", api_id_monitor, api_hash_monitor)
# client_commentator = await connect_telegram_account("accounts/commentator_account", api_id_commentator, api_hash_commentator)