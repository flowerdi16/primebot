import html
import math

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from config import ADMIN_CHAT_ID, ADMIN_IDS, PAGE_SIZE, SECTIONS
from database import get_forward_user, get_user, get_votes, count_votes
from keyboards import list_keyboard

router = Router()


def is_admin(user_id, chat_id):
    return user_id in ADMIN_IDS and chat_id == ADMIN_CHAT_ID


def profile_text(user):
    if user["username"]:
        return "@" + user["username"]
    return f'tg://user?id={user["user_id"]}'


async def render_list(section_id, page):
    total = await count_votes(section_id)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    entries = await get_votes(section_id, page * PAGE_SIZE, PAGE_SIZE)

    lines = [f"<b>{html.escape(SECTIONS[section_id])}</b>", ""]
    if not entries:
        lines.append("Ответов пока нет.")
    else:
        for index, entry in enumerate(entries, start=page * PAGE_SIZE + 1):
            user_link = html.escape(profile_text(entry))
            full_name = html.escape(entry["full_name"])
            answer = html.escape(entry["answer"])
            lines.append(
                f"{index}) {user_link} ({full_name}) | "
                f"Проголосовал: «{answer}»"
            )
    lines.extend(["", f"Всего: {total} | Страница {page + 1}/{total_pages}"])
    return "\n".join(lines), list_keyboard(section_id, page, total_pages)


@router.message(Command("list"))
async def list_command(message: Message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    text, keyboard = await render_list(1, 0)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("list:"))
async def list_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.message.chat.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        _, section_str, page_str = callback.data.split(":")
        section_id, page = int(section_str), int(page_str)
    except (ValueError, TypeError):
        await callback.answer("Некорректная кнопка")
        return
    if section_id not in SECTIONS:
        await callback.answer("Раздел не найден")
        return
    text, keyboard = await render_list(section_id, page)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error).lower():
            raise
    await callback.answer()


@router.message(Command("almond"))
async def almond_command(message: Message):
    if not is_admin(message.from_user.id, message.chat.id):
        return
    if not message.reply_to_message:
        await message.reply("Ответьте командой /almond на пересланное ботом сообщение.")
        return

    user_id = await get_forward_user(message.chat.id, message.reply_to_message.message_id)
    if user_id is None:
        await message.reply("Это сообщение не найдено среди пересланных ботом.")
        return

    user = await get_user(user_id)
    if user is None:
        await message.reply("Данные пользователя не найдены.")
        return

    username = "@" + user["username"] if user["username"] else "Отсутствует"
    link = (
        "https://t.me/" + user["username"]
        if user["username"] else f"tg://user?id={user_id}"
    )
    await message.reply(
        f'Имя: {user["full_name"]}\n'
        f"Username: {username}\n"
        f"Telegram ID: {user_id}\n"
        f"Ссылка: {link}",
        parse_mode=None,
    )
