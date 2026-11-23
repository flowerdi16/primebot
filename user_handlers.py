from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramAPIError

from config import ADMIN_CHAT_ID, SECTIONS, NOMINATIONS
from database import get_completed, save_user, save_vote, remember_forward
from keyboards import sections_keyboard, cancel_keyboard, nomination_keyboard

router = Router()


class VoteState(StatesGroup):
    waiting_for_name = State()


async def show_menu(message: Message, user_id: int):
    completed = await get_completed(user_id)
    if len(completed) == len(SECTIONS):
        await message.answer("Вы уже заполнили все 7 разделов. Спасибо!")
        return
    await message.answer(
        f"Выберите раздел. Заполнено: {len(completed)} из {len(SECTIONS)}.\n"
        "В каждый раздел можно отправить имя только один раз.",
        reply_markup=sections_keyboard(completed),
    )


@router.message(CommandStart(), F.chat.type == "private")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await save_user(message.from_user)
    await show_menu(message, message.from_user.id)


@router.callback_query(F.data.startswith("choose:"))
async def choose_section(callback: CallbackQuery, state: FSMContext):
    if callback.message.chat.type != "private":
        await callback.answer("Только в личном чате", show_alert=True)
        return
    try:
        section_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректная номинация", show_alert=True)
        return
    completed = await get_completed(callback.from_user.id)
    if section_id not in NOMINATIONS or section_id in completed:
        await callback.answer("Эта номинация уже заполнена или недоступна.", show_alert=True)
        return
    await state.clear()
    nomination = NOMINATIONS[section_id]
    await callback.message.answer(
        f"{nomination['name']}\n\n{nomination['description']}",
        reply_markup=nomination_keyboard(section_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vote:"))
async def vote_button(callback: CallbackQuery, state: FSMContext):
    if callback.message.chat.type != "private":
        await callback.answer("Только в личном чате", show_alert=True)
        return
    try:
        section_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректная номинация", show_alert=True)
        return
    completed = await get_completed(callback.from_user.id)
    if section_id not in NOMINATIONS or section_id in completed:
        await callback.answer("Вы уже голосовали в этой номинации!", show_alert=True)
        return
    await state.set_state(VoteState.waiting_for_name)
    await state.update_data(section_id=section_id)
    await callback.message.answer(
        f"{SECTIONS[section_id]}\n\nНапишите имя кандидата или название канала "
        "одним текстовым сообщением. После отправки изменить голос нельзя.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_nominations")
async def back_to_nominations(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_menu(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено")
    await show_menu(callback.message, callback.from_user.id)


@router.message(StateFilter(VoteState.waiting_for_name), F.chat.type == "private")
async def receive_name(message: Message, state: FSMContext, bot):
    if not message.text or message.text.startswith("/"):
        await message.answer("Отправьте имя обычным текстом или нажмите «Отмена».")
        return

    answer = message.text.strip()
    if not answer or len(answer) > 100 or "\n" in answer:
        await message.answer("Имя должно быть одной строкой длиной от 1 до 100 символов.")
        return

    data = await state.get_data()
    section_id = data.get("section_id")
    if section_id not in SECTIONS:
        await state.clear()
        await message.answer("Выберите раздел заново через /start.")
        return

    await save_user(message.from_user)
    saved = await save_vote(message.from_user, section_id, answer)
    await state.clear()
    if not saved:
        await message.answer("Вы уже отправляли ответ в этот раздел.")
        await show_menu(message, message.from_user.id)
        return

    # Пересылаем исходное сообщение без подписи.
    try:
        forwarded = await bot.forward_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await remember_forward(ADMIN_CHAT_ID, forwarded.message_id, message.from_user.id)
    except TelegramAPIError:
        # Ответ уже сохранён. Ошибку фиксируем в логах, не обещая доставку.
        import logging
        logging.exception("Не удалось переслать сообщение в админский чат")

    await message.answer("Имя принято! Повторная отправка в этот раздел недоступна.")
    await show_menu(message, message.from_user.id)


@router.message(F.chat.type == "private")
async def other_private_message(message: Message):
    completed = await get_completed(message.from_user.id)
    if len(completed) == len(SECTIONS):
        await message.answer("Вы уже заполнили все 7 разделов. Новые ответы недоступны.")
    else:
        await message.answer("Для выбора раздела нажмите /start.")
