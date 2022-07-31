# -*- coding: utf-8 -*-
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
message_path = ""
channel_messages_path = ""
min_message_id = 0
all_messages = []


def create_path(folder):
    # checking if the path exists
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
    global all_messages  # список всех сообщений
    offset_msg = 0  # номер записи, с которой начинается считывание
    limit_msg = 100  # максимальное число записей, передаваемых за один раз
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
            limit=limit_msg, max_id=0, min_id=min_message_id,
            hash=0))
        if not history.messages:
            break
        messages = history.messages
        grouped_id = None

        for message in messages:
            global message_path
            if message.grouped_id and grouped_id != message.grouped_id:
                print("\n--------------------------------\n")
                print(f'Save Fist grouped post group_id {message.grouped_id}: post_id - {message.id}')

                grouped_id = message.grouped_id

                msg_dict = await grab_message(message=message, is_first_in_group=True)

                all_messages.append(msg_dict)
                with open(f'{channel_messages_path}', 'w', encoding='utf8') as outfile:
                    json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
                print(f'Post {message.id} saved...')

            elif message.grouped_id:
                print(f'\nAdd data to post is grouped_id {message.grouped_id}:  post_id - {message.id}')
                msg_dict = await grab_message(message=message, msg_dict=msg_dict)

                # если это элемент группы постов то заменяем последние сообщение
                all_messages[-1] = msg_dict
                with open(f'{channel_messages_path}', 'w', encoding='utf8') as outfile:
                    json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
                print(f'Post {message.id} saved...')
            else:
                print("\n--------------------------------\n")
                msg_dict = await grab_message(message)

                all_messages.append(msg_dict)
                with open(f'{channel_messages_path}', 'w', encoding='utf8') as outfile:
                    json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
                print(f'Post {message.id} saved...')

        offset_msg = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break

    print("\n\n\nSort message...")
    all_messages.sort(key=lambda elem: elem["id"], reverse=True)
    with open(f'{channel_messages_path}', 'w', encoding='utf8') as outfile:
        json.dump(all_messages, outfile, ensure_ascii=False, cls=DateTimeEncoder)
    print(f'Sorted message  saved to {channel_messages_path}...')


async def grab_message(message, msg_dict=None, is_first_in_group=False):
    if msg_dict is None:
        msg_dict = {"id": 0, "text": "", "links": [], "media": []}
    global message_path
    if message.grouped_id:
        is_grouped = True
    else:
        is_grouped = False
    if not is_grouped or is_first_in_group:
        message_path = f'{channel_dir}/{str(message.id)}'
        create_path(message_path)
        msg_dict["id"] = message.id
    post_id = message.id
    post_message = message.message if message.message else ""
    entities = message.get_entities_text()
    entities_list = []
    for entities in entities:
        entities_list.append(entities[1])
    try:
        print("Download media...")
        await client.download_media(message.media, message_path + "/" + str(message.id))
    except Exception as e:
        print(e)

    if is_grouped and not is_first_in_group:
        msg_dict["text"] += ("\n" + post_message) if post_message else ""
        msg_dict["links"] += entities_list
        msg_dict["media"] = os.listdir(message_path)
    else:
        msg_dict = {"id": post_id, "text": post_message,
                    "links": entities_list,
                    "media": os.listdir(message_path)}
    return msg_dict


async def main():
    # url = input("Enter the link to the telegram channel or chat: ")
    url = "https://t.me/kherson_baza"

    split_url = url.split("/")
    global channel_dir, channel_messages_path, min_message_id, all_messages
    channel_name = split_url[len(split_url) - 1]
    channel_dir = path + "/" + channel_name
    channel_messages_path = channel_dir + ".json"
    if os.path.exists(channel_messages_path):
        with open(channel_messages_path, encoding='utf-8') as data_file:
            all_messages = json.load(data_file)
            min_message_id = all_messages[0]["id"]
            print(f'\n\n\nLast saved message Id is {min_message_id}')
    else:
        if os.path.exists(channel_dir):
            try:
                shutil.rmtree(channel_dir)
            except Exception as e:
                print(e)
            create_path(channel_dir)

    channel = await client.get_entity(url)

    # await dump_all_participants(channel)
    await dump_all_messages(channel)
    print(f'parsing is over, the data from the channel {channel_name} is saved...')

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
