from typing import Any
from urllib.parse import urlparse

SUPPORTED_PROTOCOLS = frozenset({"socks5", "socks4", "http"})


def normalize_protocol(value: str) -> str:
    protocol = value.strip().lower()
    if protocol in ("https", "http"):
        return "http"
    if protocol in SUPPORTED_PROTOCOLS:
        return protocol
    raise ValueError(f"Неподдерживаемый тип прокси: {value}")


def parse_proxy_line(line: str) -> dict[str, Any]:
    """Парсит строку прокси в нормализованный dict."""
    raw = line.strip()
    if not raw or raw.startswith("#"):
        raise ValueError("Пустая строка")

    if "://" in raw:
        parsed = urlparse(raw)
        if not parsed.hostname or not parsed.port:
            raise ValueError(f"Некорректный URL прокси: {raw}")
        return {
            "protocol": normalize_protocol(parsed.scheme),
            "host": parsed.hostname,
            "port": parsed.port,
            "username": parsed.username or None,
            "password": parsed.password or None,
        }

    parts = raw.split(":")
    if len(parts) == 2:
        host, port_str = parts
        username = password = None
    elif len(parts) == 4:
        host, port_str, username, password = parts
    else:
        raise ValueError(
            "Формат: host:port, host:port:user:pass или socks5://user:pass@host:port"
        )

    return {
        "protocol": "socks5",
        "host": host.strip(),
        "port": int(port_str.strip()),
        "username": username.strip() if username else None,
        "password": password.strip() if password else None,
    }


def proxy_to_telethon(proxy: dict[str, Any]) -> tuple:
    """Конвертирует запись прокси в кортеж Telethon (proxy_type, addr, port, ...)."""
    protocol = normalize_protocol(proxy["protocol"])
    port = int(proxy["port"])
    username = proxy.get("username") or None
    password = proxy.get("password") or None
    if username or password:
        return (protocol, proxy["host"], port, True, username, password)
    return (protocol, proxy["host"], port)


def format_proxy_display(proxy: dict[str, Any]) -> str:
    auth = ""
    if proxy.get("username"):
        auth = f"{proxy['username']}:***@"
    return f"{proxy['protocol']}://{auth}{proxy['host']}:{proxy['port']}"


def parse_bulk_proxies(text: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parsed = parse_proxy_line(line)
        key = f"{parsed['protocol']}:{parsed['host']}:{parsed['port']}"
        if key in seen:
            continue
        seen.add(key)
        result.append(parsed)
    if not result:
        raise ValueError("Не найдено ни одной валидной строки прокси")
    return result
