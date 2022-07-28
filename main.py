# https://proglib.io/p/pishem-prostoy-grabber-dlya-telegram-chatov-na-python-2019-11-06
# https://t.me/kherson_baza
'''
    {
        "id": 910,
        "media": [
            "media/911.jpg”,
            "media/910.mp4”
        ],
        "text": "Колабораціонізм. Рашизм.\n  Шамрай Аліна\n  21.06.1989 р.н.\n Взаємодія з окупаційною владою…”,
        "links": [
            "https://www.facebook.com/profile.php?id=100013324181103",
            "https://ok.ru/profile/579222091407"
        ]
    }
'''
import asyncio
import configparser
import json
import os

from telethon.sync import TelegramClient
from telethon import connection

# для корректного переноса времени сообщений в json
from datetime import date, datetime

# классы для работы с каналами
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

# класс для работы с сообщениями
from telethon.tl.functions.messages import GetHistoryRequest

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id = int(config['Telegram']['api_id'])
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']

path = "./.data"
channel_dir = ""


def create_path(folder):
    # Проверяем существует путь или нет
    isExist = os.path.exists(folder)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(folder)
        print("Директория " + folder + " создана..")


create_path(path)

"""
proxy = (proxy_server, proxy_port, proxy_key)
client = TelegramClient(username, api_id, api_hash,
                        connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
                        proxy=proxy)
"""
client = TelegramClient(username, api_id, api_hash)

client.start()


async def dump_all_participants(channel):
    """Записывает json-файл с информацией о всех участниках канала/чата"""
    offset_user = 0  # номер участника, с которого начинается считывание
    limit_user = 100  # максимальное число записей, передаваемых за один раз

    all_participants = []  # список всех участников канала
    filter_user = ChannelParticipantsSearch('')

    while True:
        participants = await client(GetParticipantsRequest(channel,
                                                           filter_user, offset_user, limit_user, hash=0))
        if not participants.users:
            break
        all_participants.extend(participants.users)
        offset_user += len(participants.users)

    all_users_details = []  # список словарей с интересующими параметрами участников канала

    for participant in all_participants:
        all_users_details.append({"id": participant.id,
                                  "first_name": participant.first_name,
                                  "last_name": participant.last_name,
                                  "user": participant.username,
                                  "phone": participant.phone,
                                  "is_bot": participant.bot})

    with open('channel_users.json', 'w', encoding='utf8') as outfile:
        json.dump(all_users_details, outfile, ensure_ascii=False)


async def dump_all_messages(channel):
    """Записывает json-файл с информацией о всех сообщениях канала/чата"""
    offset_msg = 0  # номер записи, с которой начинается считывание
    offset_msg = 25  # номер записи, с которой начинается считывание
    limit_msg = 100  # максимальное число записей, передаваемых за один раз

    all_messages = []  # список всех сообщений
    total_messages = 0
    total_count_limit = 0  # поменяйте это значение, если вам нужны не все сообщения

    class DateTimeEncoder(json.JSONEncoder):
        """Класс для сериализации записи дат в JSON"""

        def default(self, o):
            if isinstance(o, datetime):
                return o.isoformat()
            if isinstance(o, bytes):
                return list(o)
            return json.JSONEncoder.default(self, o)

    while True:
        history = await client(GetHistoryRequest(
            peer=channel,
            offset_id=offset_msg,
            offset_date=None, add_offset=0,
            limit=limit_msg, max_id=0, min_id=0,
            hash=0))
        if not history.messages:
            break
        messages = history.messages
        for message in messages:
            print("Сохраняется пост ", message.id)
            message_path = "{0}/{1}/{2}".format(path, channel_dir, str(message.id))
            create_path(message_path)
            # all_messages.append(message.to_dict())
            msg = message.to_dict()
            await  client.download_media(message.media, message_path)
            all_messages.append(msg)

            # if None is message.video:
            #     video = ""
            # else:
            #     video = message.video
            # all_messages.append({"id": message.id,
            #                      "text": message.text, "raw_text": message.raw_text,
            #                      })
        # {"photo": message.photo, "video": message.video}
        offset_msg = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break

    with open('channel_messages.json', 'w', encoding='utf8') as outfile:
        json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)


async def main():
    # url = input("Введите ссылку на телеграм канал или чат: ")
    url = "https://t.me/kherson_baza"

    split_url = url.split("/")
    global channel_dir
    channel_dir = split_url[len(split_url) - 1]

    create_path(path + "/" + channel_dir)

    channel = await client.get_entity(url)
    # await dump_all_participants(channel)
    await dump_all_messages(channel)


with client:
    client.loop.run_until_complete(main())

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # await main()
    asyncio.run(main())
    pass
