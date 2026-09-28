#!/usr/bin/env python3

import os
import sys
import getpass
import shlex
import argparse


def get_prompt() -> str:
    """Формирует приглашение из имени пользователя, узла и каталога."""
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
    """Разбирает строку shell, возвращая None при ошибке кавычек."""
    try:
        return shlex.split(line)
    except ValueError as e:
        print(f"Ошибка разбора: {e}", file=sys.stderr)
        return None


def cmd_ls(args):
    """Выводит имя команды ls и переданные аргументы."""
    print("ls: команда вызвана с аргументами:", args)
    if not args:
        print("  (аргументов нет)")


def cmd_cd(args):
    """Выводит имя команды cd и переданные аргументы."""
    print("cd: команда вызвана с аргументами:", args)
    if not args:
        print("  (аргументов нет)")


def cmd_echo(args):
    """Выводит аргументы, объединенные пробелами."""
    print(" ".join(args))

COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "echo": cmd_echo,
}


def execute_line(line: str, source: str = "") -> bool:
    """Выполняет команду и возвращает False для команды exit."""
    args = parse_line(line)
    if args is None:
        if source:
            print(f"Ошибка в стартовом скрипте ({source}): некорректная строка",
                  file=sys.stderr)
        return True
    if not args:
        return True

    name, *rest = args
    if name == "exit":
        print("Выход.")
        return False

    handler = COMMANDS.get(name)
    if handler is None:
        print(f"{name}: команда не найдена", file=sys.stderr)
        if source:
            print(f"Ошибка в стартовом скрипте ({source})", file=sys.stderr)
        return True

    try:
        handler(rest)
    except Exception as error:
        print(f"{name}: ошибка выполнения: {error}", file=sys.stderr)
        if source:
            print(f"Ошибка в стартовом скрипте ({source})", file=sys.stderr)
    return True


def run_startup_script(script_path: str) -> bool:
    """Выполняет команды из файла и сообщает о некорректных строках."""
    try:
        with open(script_path, "r", encoding="utf-8") as script:
            for line_number, line in enumerate(script, start=1):
                command = line.rstrip("\r\n")
                if not command.strip():
                    continue
                print(f"{get_prompt()}{command}")
                if not execute_line(command, f"{script_path}:{line_number}"):
                    return False
    except OSError as error:
        print(f"Ошибка запуска стартового скрипта '{script_path}': {error}",
              file=sys.stderr)
    return True


def build_argument_parser() -> argparse.ArgumentParser:
    """Создает парсер параметров конфигурации приложения."""
    parser = argparse.ArgumentParser(description="Эмулятор командной строки")
    parser.add_argument("--vfs-path", help="путь к расположению VFS")
    parser.add_argument("--startup-script", help="путь к стартовому скрипту")
    return parser


def repl():
    """Запускает интерактивный цикл чтения и выполнения команд."""
    while True:
        try:
            line = input(get_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not execute_line(line):
            break


def main(argv=None):
    """Выводит параметры запуска, выполняет сценарий и запускает REPL."""
    args = build_argument_parser().parse_args(argv)
    print("Параметры запуска:")
    print(f"  Путь к VFS: {args.vfs_path}")
    print(f"  Стартовый скрипт: {args.startup_script}")

    if args.startup_script and not run_startup_script(args.startup_script):
        return
    repl()


if __name__ == "__main__":
    main()