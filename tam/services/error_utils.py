"""Человекочитаемые сообщения об ошибках Telethon/прокси."""


def format_exception(exc: BaseException) -> str:
    """Извлекает понятный текст, в т.ч. когда Telethon маскирует ошибку прокси."""
    message = str(exc).strip()
    if message and message != "ConnectionError() takes no keyword arguments":
        if not _is_generic_typeerror(message):
            return message

    cause = exc.__cause__ or exc.__context__
    if cause and cause is not exc:
        cause_msg = format_exception(cause)
        if cause_msg:
            return cause_msg

    if hasattr(exc, "error_code") and message:
        return message

    name = type(exc).__name__
    if name in ("ReplyError", "ProxyError", "ProxyConnectionError", "ProxyTimeoutError"):
        return message or name

    if name == "TypeError" and _is_generic_typeerror(message):
        return (
            "Не удалось подключиться через прокси. "
            "Проверьте адрес, порт, логин/пароль и доступность прокси."
        )

    if name == "ConnectionError" and not message:
        return "Ошибка сетевого подключения (прокси или Telegram недоступны)"

    return message or name


def _is_generic_typeerror(message: str) -> bool:
    return "ConnectionError() takes no keyword arguments" in message
