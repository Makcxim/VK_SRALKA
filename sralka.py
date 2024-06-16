import asyncio
import json
from typing import List, Optional

import openai
from decouple import config
from vkbottle import PhotoMessageUploader, ABCHTTPClient
from vkbottle.api import API
from vkbottle.bot import BotLabeler, Message
from vkbottle.user import User

from ai_utils import generate_ai_answer
from utils import custom_serializer, random_delay, validate_group_id, create_if_not_exists_groups_json

labeler = BotLabeler()
admin_chat_id = config('VK_ADMIN_CHAT_ID', default=0)


async def walls_checker(group_id: int, count: int = 1) -> str:
    group_id = validate_group_id(group_id)
    wall_post = await api.wall.get(owner_id=group_id, count=count, extended=False)
    delim = '\n'
    answer = f'{wall_post.items[0].id}:\n{wall_post.items[0].text + (delim if wall_post.items[0].text else None) + wall_post.items[0].copy_history[0].text if wall_post.items[0].copy_history else ''}'
    return answer


async def attachments_uploader(
    api_wall_data, peer_id: int, http_client: ABCHTTPClient
) -> Optional[List[str]]:
    if not api_wall_data.items[0].attachments:
        return None
    message = api_wall_data.items[0].attachments

    attachments = []
    photo_attachments = [attachment.photo for attachment in message if attachment.photo]

    if photo_attachments:
        uploader = PhotoMessageUploader(api=api, generate_attachment_strings=True)
        for photo in photo_attachments:
            url = photo.sizes[-1].url
            bytes_photo = await http_client.request_content(url=url)
            attachments.append(
                await uploader.upload(file_source=bytes_photo, peer_id=peer_id)
            )

    return attachments


@labeler.message(text=['/att <group_id>', '/att'])
async def manual_attachment_uploader_test(message: Message, group_id: int = 0):

    group_id = validate_group_id(group_id)

    try:
        wall_data = await api.wall.get(owner_id=group_id, count=1, extended=False)
        attachments = await attachments_uploader(
            api_wall_data=wall_data, peer_id=message.peer_id, http_client=message.ctx_api.http_client
        )
        await message.answer(message='test message', attachment=attachments)
    except Exception as e:
        await asyncio.sleep(5 + random_delay(0, 3))
        await message.answer(f'Error: {e}')
        wall_data = await api.wall.get(owner_id=group_id, count=1, extended=False)
        attachments = await attachments_uploader(
            api_wall_data=wall_data, peer_id=message.peer_id, http_client=message.ctx_api.http_client
        )
        await message.answer(message='test message', attachment=attachments)


@labeler.message(text=['/check <group_id>', '/check'])
async def manual_group_checker_test(message: Message, group_id: int = None):
    group_id = validate_group_id(group_id)
    try:
        answer = await walls_checker(group_id, count=1)
        await message.answer(answer)
    except Exception as e:
        await asyncio.sleep(5 + random_delay(0, 3))
        await message.answer(f'Error: {e}')
        await message.answer(await walls_checker(group_id, count=1))


@labeler.message(text=['/prompt_test <text>'])
async def manual_prompt_test(message: Message, text: str = ''):
    if not text:
        return await message.answer('No text provided')

    ai_answer = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{
                'role': 'assistant', 'content': 'You are a helpful assistant.'
            },
            {
                'role': 'user', 'content': text
            }
        ]
    )
    mem = str(ai_answer['choices'][0]['message']['content'])
    await message.answer(f'AI_ANSWER:{mem}')


@labeler.message()
async def every_message(message: Message):
    print(message)


async def loop_walls_checker(groups_list: list = None) -> None:
    if groups_list is None:
        groups_list = [config('VK_TEST_GROUP_ID')]
        if not groups_list[0]:
            raise ValueError('No groups provided')

    print('Start loop_walls_checker')
    for group_id in groups_list:
        try:
            wall_post = await api.wall.get(owner_id=group_id, count=1, extended=True)

            if wall_post.items[0].is_pinned:
                wall_post = await api.wall.get(owner_id=group_id, count=1, offset=1, extended=True)

            post_id = wall_post.items[0].id
            groups_data = json.loads(open('groups.json', 'r', encoding='utf-8').read())

            str_group_id = str(group_id)

            if (str_group_id not in groups_data.keys()) or (
                    groups_data[str_group_id]['last_post_id']
                    and groups_data[str_group_id]['last_post_id'] != post_id
            ):
                group_name = wall_post.groups[-1].name
                post_link = f'https://vk.com/club{wall_post.groups[-1].id}/?w=wall-{wall_post.groups[-1].id}_{post_id}'
                ost_link = f'https://vk.com/public{wall_post.groups[-1].id}/?w=wall-{wall_post.groups[-1].id}_{post_id}'
                full_post_text = (
                        wall_post.items[0].text
                        + ('\n' if wall_post.items[0].text else '')
                        + (
                            wall_post.items[0].copy_history[0].text
                            if wall_post.items[0].copy_history
                            else ''
                        )
                )

                message = (
                    f'NEW POST\n{group_name}\n{post_link}\n{ost_link}\n'
                    f'Last post with id:{post_id}:\n{full_post_text}'
                )

                groups_data[str_group_id] = {
                    'group_name': group_name,
                    'last_post_id': post_id,
                    'last_post_text': full_post_text,
                    'link1': post_link,
                    'link2': ost_link,
                }
                with open('groups.json', 'w', encoding='utf-8') as f:
                    json.dump(groups_data, f, indent=4, ensure_ascii=False, default=custom_serializer)

                await asyncio.sleep(5 + random_delay(0, 3))
                attachments = await attachments_uploader(
                    wall_post, peer_id=admin_chat_id, http_client=user.api.http_client
                )

                ai_answer = await generate_ai_answer(text=full_post_text)
                message += f'\nAI_ANSWER:\n{ai_answer}'
                try:
                    await user.api.messages.send(
                        chat_id=admin_chat_id, message=message, random_id=0, attachment=attachments
                    )
                except Exception as e:
                    await asyncio.sleep(5 + random_delay(0, 3))
                    await user.api.messages.send(chat_id=admin_chat_id, message=f'Error: {e}', random_id=0)

                    await asyncio.sleep(5 + random_delay(0, 3))
                    await user.api.messages.send(
                        chat_id=admin_chat_id, message=message, random_id=0, attachment=attachments
                    )

                if config('VK_COMMENT_MODE', '') or group_id == config('VK_TEST_GROUP_ID', default=0):
                    await user.api.wall.create_comment(owner_id=group_id, post_id=post_id, message='👍')

        except Exception as e:
            await asyncio.sleep(5 + random_delay(0, 3))
            await user.api.messages.send(chat_id=admin_chat_id, message=f'Error: {e}', random_id=0)
        await asyncio.sleep(5 + random_delay(1, 5))
    print('End loop_walls_checker')

    user.loop.call_later(
        300 + random_delay(0, 31),
        lambda: user.loop.create_task(
            loop_walls_checker(config('VK_GROUPS_ID', default=[]).split(','))
        ),
    )


async def set_http_client(user_: User):
    from aiohttp import ClientSession
    from vkbottle import AiohttpClient

    user_.api.http_client = AiohttpClient(session=ClientSession())


if __name__ == '__main__':
    create_if_not_exists_groups_json()

    token = config('VK_TOKEN', default='')
    access_token = config('VK_ACCESS_TOKEN', default='')
    openai.api_key = config('OPENAI_API_KEY', default='')

    api = API(access_token)
    user = User(token)

    user.loop_wrapper.add_task(set_http_client(user))
    user.labeler.load(labeler)

    user.loop.call_later(
        10 + random_delay(3, 5),
        lambda: user.loop.create_task(
            loop_walls_checker(config('VK_GROUPS_ID', default=[]).split(','))
        ),
    )

    user.run_forever()
