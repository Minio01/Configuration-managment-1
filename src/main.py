#!/usr/bin/env python3
"""
Эмулятор командной строки UNIX-подобной ОС.
Этап 1: REPL + парсер с кавычками + заглушки ls/cd + exit.
"""

import os
import sys
import getpass
import shlex


def get_prompt() -> str:
    """
    Формирует приглашение вида username@hostname:cwd$
    на основе реальных данных ОС.
    """
    try:
        username = getpass.getuser()
    except Exception:
        username = os.environ.get("USER", os.environ.get("USERNAME", "user"))

    hostname = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME")
    if not hostname:
        try:
            import socket
            hostname = socket.gethostname()
        except Exception:
            hostname = "localhost"

    cwd = os.getcwd()

    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]

    return f"{username}@{hostname}:{cwd}$ "


def parse_line(line: str):
    """
    Разбирает строку на список аргументов, корректно обрабатывая кавычки.
    Использует shlex (аналог того, что делает настоящий shell).

    Возвращает список аргументов или None, если строка некорректна
    (например, незакрытая кавычка).
    """
    try:
        return shlex.split(line)
    except ValueError as e:
        print(f"Ошибка разбора: {e}", file=sys.stderr)
        return None


def cmd_ls(args):
    """Заглушка ls: печатает имя команды и аргументы."""
    print("ls: команда вызвана с аргументами:", args)
    if not args:
        print("  (аргументов нет)")


def cmd_cd(args):
    """Заглушка cd: печатает имя команды и аргументы."""
    print("cd: команда вызвана с аргументами:", args)
    if not args:
        print("  (аргументов нет)")


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
}


def repl():
    """Запускает интерактивный цикл чтения и выполнения команд."""
    while True:
        try:
            line = input(get_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line.strip():
            continue

        args = parse_line(line)
        if args is None:
            continue
        if not args:
            continue

        name, *rest = args

        if name == "exit":
            print("Выход.")
            break

        handler = COMMANDS.get(name)
        if handler is None:
            print(f"{name}: команда не найдена", file=sys.stderr)
            continue

        try:
            handler(rest)
        except Exception as e:
            print(f"{name}: ошибка выполнения: {e}", file=sys.stderr)


if __name__ == "__main__":
    repl()