import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from tam.bot import keyboards as kb
from tam.db.models import Account, Message as DBMessage, Task

router = Router()


class AddAccount(StatesGroup):
    phone = State()
    code = State()
    password = State()


class CreateMessage(StatesGroup):
    target = State()
    accounts = State()
    text = State()
    repeat = State()
    interval = State()
    delay = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🤖 Бот для управления аккаунтами\n\nВыберите действие:",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == "📱 Аккаунты")
async def accounts_handler(message: Message):
    await message.answer("Управление аккаунтами:", reply_markup=kb.accounts_menu())


@router.message(F.text == "✉️ Сообщения")
async def messages_handler(message: Message):
    await message.answer("Управление сообщениями:", reply_markup=kb.messages_menu())


@router.message(F.text == "🔙 Назад")
async def back_handler(message: Message):
    await message.answer("Главное меню:", reply_markup=kb.main_menu())


@router.message(F.text == "➕ Добавить аккаунт")
async def add_account_start(message: Message, state: FSMContext):
    await state.set_state(AddAccount.phone)
    await message.answer("Введите номер телефона в формате +79123456789:")


@router.message(AddAccount.phone)
async def add_account_phone(message: Message, state: FSMContext, account_manager):
    phone = message.text.strip()
    client, status = await account_manager.add_account(phone)

    if status == "code_sent":
        await state.update_data(phone=phone, client=client)
        await state.set_state(AddAccount.code)
        await message.answer("Код отправлен! Введите код подтверждения:")
    else:
        await message.answer("Ошибка при добавлении аккаунта")
        await state.clear()


@router.message(AddAccount.code)
async def add_account_code(message: Message, state: FSMContext, account_manager, db):
    data = await state.get_data()
    code = message.text.strip()

    result, status = await account_manager.verify_code(data["client"], data["phone"], code)

    if status == "password_required":
        await state.update_data(code=code)
        await state.set_state(AddAccount.password)
        await message.answer("Требуется двухфакторная аутентификация. Введите пароль:")
    elif status == "success":
        async with db.session_maker() as session:
            account = Account(**result)
            session.add(account)
            await session.commit()
        await message.answer("✅ Аккаунт успешно добавлен!", reply_markup=kb.accounts_menu())
        await state.clear()
    elif status == "invalid_code":
        await message.answer("❌ Неверный код. Попробуйте еще раз:")
    else:
        await message.answer("❌ Ошибка при добавлении аккаунта")
        await state.clear()


@router.message(AddAccount.password)
async def add_account_password(message: Message, state: FSMContext, account_manager, db):
    data = await state.get_data()
    password = message.text.strip()

    result, status = await account_manager.verify_code(
        data["client"], data["phone"], data.get("code", ""), password
    )

    if status == "success":
        async with db.session_maker() as session:
            account = Account(**result)
            session.add(account)
            await session.commit()
        await message.answer("✅ Аккаунт успешно добавлен!", reply_markup=kb.accounts_menu())
    else:
        await message.answer("❌ Ошибка при добавлении аккаунта")

    await state.clear()


@router.message(F.text == "📋 Список аккаунтов")
async def list_accounts(message: Message, db):
    async with db.session_maker() as session:
        result = await session.execute(select(Account).where(Account.is_active == True))
        accounts = result.scalars().all()

    if not accounts:
        await message.answer("Нет активных аккаунтов")
        return

    text = "📱 Активные аккаунты:\n\n"
    for acc in accounts:
        status = "🟢" if acc.is_active else "🔴"
        text += f"{status} {acc.first_name or 'Без имени'}\n"
        text += f"   📞 {acc.phone}\n"
        text += f"   🆔 {acc.username or 'Без username'}\n\n"

    await message.answer(text)


@router.message(F.text == "✏️ Создать сообщение")
async def create_message_start(message: Message, state: FSMContext):
    await state.set_state(CreateMessage.target)
    await message.answer("Введите целевой чат (username или ID):")


@router.message(CreateMessage.target)
async def create_message_target(message: Message, state: FSMContext, db):
    await state.update_data(target=message.text.strip())

    async with db.session_maker() as session:
        result = await session.execute(select(Account).where(Account.is_active == True))
        accounts = result.scalars().all()

    if not accounts:
        await message.answer("Нет активных аккаунтов")
        await state.clear()
        return

    await state.update_data(accounts=accounts, selected=[])
    await state.set_state(CreateMessage.accounts)
    await message.answer("Выберите аккаунты:", reply_markup=kb.account_selection(accounts))


@router.callback_query(F.data.startswith("toggle_acc_"))
async def toggle_account(callback: CallbackQuery, state: FSMContext):
    account_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("selected", [])

    if account_id in selected:
        selected.remove(account_id)
    else:
        selected.append(account_id)

    await state.update_data(selected=selected)
    await callback.message.edit_reply_markup(
        reply_markup=kb.account_selection(data["accounts"], selected)
    )
    await callback.answer()


@router.callback_query(F.data == "accounts_done")
async def accounts_selected(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("selected"):
        await callback.answer("Выберите хотя бы один аккаунт", show_alert=True)
        return

    await state.set_state(CreateMessage.text)
    await callback.message.answer("Введите текст сообщения (поддерживается Markdown):")
    await callback.answer()


@router.message(CreateMessage.text)
async def create_message_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(CreateMessage.repeat)
    await message.answer("Количество повторов (по умолчанию 1):")


@router.message(CreateMessage.repeat)
async def create_message_repeat(message: Message, state: FSMContext):
    try:
        repeat = int(message.text.strip())
        await state.update_data(repeat=repeat)
        await state.set_state(CreateMessage.interval)
        await message.answer("Интервал между сообщениями (в секундах, по умолчанию 30):")
    except ValueError:
        await message.answer("Введите число:")


@router.message(CreateMessage.interval)
async def create_message_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        await state.update_data(interval=interval)
        await state.set_state(CreateMessage.delay)
        await message.answer("Задержка между аккаунтами (в секундах, по умолчанию 10):")
    except ValueError:
        await message.answer("Введите число:")


@router.message(CreateMessage.delay)
async def create_message_delay(message: Message, state: FSMContext, db, message_sender):
    try:
        delay = int(message.text.strip())
        data = await state.get_data()

        async with db.session_maker() as session:
            result = await session.execute(select(Account).where(Account.id.in_(data["selected"])))
            accounts = result.scalars().all()

            task = Task(
                target_chat=data["target"],
                message_text=data["text"],
                account_ids=",".join(map(str, data["selected"])),
                repeat_count=data["repeat"],
                interval=data["interval"],
                account_delay=delay,
                status="queued",
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)

        await message.answer("✅ Задача создана и запущена!", reply_markup=kb.main_menu())

        asyncio.create_task(
            message_sender.execute_task(
                task.id,
                accounts,
                data["target"],
                data["text"],
                data["repeat"],
                data["interval"],
                delay,
            )
        )

        await state.clear()
    except ValueError:
        await message.answer("Введите число:")


@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message, message_sender):
    stats = await message_sender.get_statistics()

    text = "📊 Статистика отправки:\n\n"
    text += f"✅ Успешно: {stats.get('success', 0)}\n"
    text += f"⏳ В ожидании: {stats.get('pending', 0)}\n"
    text += f"❌ Ошибок: {stats.get('error', 0)}\n"
    text += f"🚫 Flood wait: {stats.get('flood_wait', 0)}\n"
    text += f"⛔️ Запрещено: {stats.get('forbidden', 0)}\n"

    await message.answer(text)


@router.message(F.text == "📜 История")
async def history_handler(message: Message, db):
    async with db.session_maker() as session:
        result = await session.execute(
            select(DBMessage).order_by(DBMessage.created_at.desc()).limit(10)
        )
        messages = result.scalars().all()

    if not messages:
        await message.answer("История пуста")
        return

    text = "📜 Последние сообщения:\n\n"
    for msg in messages:
        status_emoji = {
            "success": "✅",
            "pending": "⏳",
            "error": "❌",
            "flood_wait": "🚫",
            "forbidden": "⛔️",
        }.get(msg.status, "❓")

        text += f"{status_emoji} {msg.target_chat}\n"
        text += f"   {msg.text[:50]}...\n"
        text += f"   {msg.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"

    await message.answer(text)
