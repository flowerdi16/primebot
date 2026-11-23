from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import SECTIONS


def sections_keyboard(completed):
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"choose:{section_id}")]
        for section_id, name in SECTIONS.items()
        if section_id not in completed
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])


def list_keyboard(section_id, page, total_pages):
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(
            text="◀ Назад", callback_data=f"list:{section_id}:{page - 1}"
        ))
    if page + 1 < total_pages:
        navigation.append(InlineKeyboardButton(
            text="Далее ▶", callback_data=f"list:{section_id}:{page + 1}"
        ))

    rows = [navigation] if navigation else []
    for start in (1, 5):
        rows.append([
            InlineKeyboardButton(
                text=f"{'• ' if n == section_id else ''}{n}",
                callback_data=f"list:{n}:0"
            )
            for n in range(start, min(start + 4, 8))
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def nomination_keyboard(section_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проголосовать", callback_data=f"vote:{section_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_nominations")],
    ])
