# -*- coding: utf-8 -*-
# https://proglib.io/p/pishem-prostoy-grabber-dlya-telegram-chatov-na-python-2019-11-06
# https://t.me/kherson_baza
# Note Telegram’s flood wait limit
# for GetHistoryRequest seems to be around 30 seconds per 10 requests, ...

# медленная закачка файлов, в пределах 60-80 Кб/сек,
# судя по всему обусловленно самим API Телеграма
# Если необходима скорость получения информации то как вариант
# можно рассмотреть сохранение чата с десктопного клиента
# с последующим парсингом сохраненных данных

# теоретически должно работать асинхронно, но по факту это не так,
# стоит более подробно рассмотреть возможность асинхронной закачки
# или возможно другой способ получения контента

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
import shutil

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
    is_exist = os.path.exists(folder)
    if not is_exist:
        # Create a new directory because it does not exist
        os.makedirs(folder)
        print("Folder " + folder + " created..")


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
    offset_msg = 0  # номер записи, с которой начинается считывание
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

    msg_dict = {}
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
        # messages.reverse()
        # messages_reverse = messages
        # messages_reverse.reverse()
        # message_path = None
        grouped_id = None

        message_path = ""
        for message in messages:
            if grouped_id != message.grouped_id:
                print("Try Save post is grouped_id: ", message.id)
                if os.path.exists(message_path):
                    msg_dict[grouped_id]["media"] = os.listdir(message_path)

                grouped_id = message.grouped_id
                all_messages.append({grouped_id: {}})
                message_path = f'{channel_dir}/{str(message.id)}'
                create_path(message_path)
                post_id = message.id
                post_text = message.text if message.text else ""
                post_message = message.message if message.message else ""
                entities = message.get_entities_text()
                entities_list = []
                for entities in entities:
                    entities_list.append(entities[1])
                try:
                    await client.download_media(message.media, message_path + "/")
                except Exception as e:
                    print(e)
                msg_dict[grouped_id] = {"id": post_id, "media": [],
                                        "text": post_text, "message": post_message,
                                        "links": entities_list}
            elif grouped_id:
                print("is grouped_id")
                post_text = message.text if message.text else ""
                post_message = message.message if message.message else ""
                entities = message.get_entities_text()
                entities_list = []
                for entities in entities:
                    entities_list.append(entities[1])
                try:
                    await client.download_media(message.media, message_path + "/")
                except Exception as e:
                    print(e)

                msg_dict[grouped_id]["text"] += f'\n{post_text}'
                msg_dict[grouped_id]["message"] += f'\n{post_message}'
                if entities_list:
                    msg_dict[grouped_id]["links"].append(entities_list)
            else:
                print("Try Save post no grouped_id: ", message.id)
                message_path = f'{channel_dir}/{str(message.id)}'
                create_path(message_path)

                post_id = message.id
                post_text = message.text if message.text else ""
                raw_text = message.raw_text if message.raw_text else ""
                post_message = message.message if message.message else ""
                entities = message.get_entities_text()
                entities_list = []
                for entities in entities:
                    entities_list.append(entities[1])
                try:
                    await client.download_media(message.media, message_path + "/" + str(message.id))
                except Exception as e:
                    print(e)
                msg_dict[message.id] = {"id": post_id,
                                        "text": post_text,
                                        "raw_text": raw_text,
                                        "message": post_message,
                                        "links": entities_list,
                                        "media": []}
                msg_dict[message.id]["media"] = os.listdir(message_path)

                all_messages.append(msg_dict)
                with open('channel_messages.json', 'w', encoding='utf8') as outfile:
                    json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
                print(f'Post {message.id} saved...')

            # msg = message.to_dict()
            # all_messages.append(msg)

        offset_msg = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break

    # with open('channel_messages.json', 'w', encoding='utf8') as outfile:
    #     # json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
    #     json.dump(msg_dict, outfile, ensure_ascii=False, cls=DateTimeEncoder)


async def main():
    # url = input("Enter the link to the telegram channel or chat: ")
    url = "https://t.me/kherson_baza"

    split_url = url.split("/")
    global channel_dir
    channel_dir = path + "/" + split_url[len(split_url) - 1]
    try:
        shutil.rmtree(channel_dir)
    except Exception as e:
        print(e)
    create_path(channel_dir)

    channel = await client.get_entity(url)

    # await dump_all_participants(channel)
    await dump_all_messages(channel)


with client:
    client.loop.run_until_complete(main())

if __name__ == '__main__':
    asyncio.run(main())
    pass
