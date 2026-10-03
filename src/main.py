#!/usr/bin/env python3

import os
import sys
import getpass
import shlex
import argparse
from dataclasses import dataclass, field
from pathlib import Path

TAIL_DEFAULT_LINES = 10


def get_username() -> str:
    """Возвращает имя пользователя реальной ОС."""
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER", os.environ.get("USERNAME", "user"))


def get_hostname() -> str:
    """Возвращает имя узла реальной ОС."""
    hostname = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME")
    if hostname:
        return hostname
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "localhost"


def get_prompt() -> str:
    """Формирует приглашение из пользователя, узла и каталога VFS."""
    return f"{get_username()}@{get_hostname()}:{virtual_cwd()}$ "


def parse_line(line: str):
    """Разбирает строку shell, возвращая None при ошибке кавычек."""
    try:
        return shlex.split(line)
    except ValueError as e:
        print(f"Ошибка разбора: {e}", file=sys.stderr)
        return None


class CommandError(Exception):
    """Ошибка выполнения команды эмулятора."""


class VFSLoadError(CommandError):
    """Ошибка чтения, формата или поиска пути в виртуальной ФС."""


@dataclass
class VFSNode:
    """Узел виртуального дерева: каталог или файл в памяти."""

    name: str
    is_directory: bool
    content: bytes = b""
    children: dict[str, "VFSNode"] = field(default_factory=dict)


class VirtualFileSystem:
    """Дерево VFS, загруженное в память без изменения источника."""

    def __init__(self, root: VFSNode, source_path: Path | None = None):
        """Сохраняет корень дерева и путь источника."""
        self.root = root
        self.source_path = source_path

    @classmethod
    def empty(cls):
        """Создает пустую VFS для запуска без параметра пути."""
        return cls(VFSNode("", True))

    @classmethod
    def load(cls, source_path: str):
        """Загружает директорию и файлы в память, не изменяя их."""
        path = Path(source_path).expanduser()
        if not path.exists():
            raise VFSLoadError(f"путь не найден: {path}")
        if path.is_symlink() or not path.is_dir():
            raise VFSLoadError(f"ожидалась директория VFS: {path}")
        try:
            root = cls._read_directory(path, "")
        except OSError as error:
            raise VFSLoadError(f"не удалось прочитать VFS: {error}") from error
        return cls(root, path.resolve())

    @classmethod
    def _read_directory(cls, path: Path, name: str) -> VFSNode:
        """Рекурсивно читает каталог в дерево узлов памяти."""
        node = VFSNode(name, True)
        entries = sorted(
            path.iterdir(), key=lambda item: item.name.casefold()
        )
        for entry in entries:
            if entry.is_symlink():
                message = f"символьные ссылки не поддерживаются: {entry}"
                raise VFSLoadError(message)
            if entry.is_dir():
                child = cls._read_directory(entry, entry.name)
                node.children[entry.name] = child
            elif entry.is_file():
                node.children[entry.name] = VFSNode(
                    entry.name, False, content=entry.read_bytes()
                )
            else:
                raise VFSLoadError(f"неподдерживаемый тип файла: {entry}")
        return node

    def resolve(self, path: str, current_path=None):
        """Находит узел по абсолютному или относительному пути."""
        parts = [] if path.startswith("/") else list(current_path or [])
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        node = self.root
        for part in parts:
            if not node.is_directory:
                raise VFSLoadError(f"не является каталогом: {part}")
            if part not in node.children:
                raise VFSLoadError(f"путь не найден: /{'/'.join(parts)}")
            node = node.children[part]
        return node, parts


@dataclass
class ShellState:
    """Состояние сеанса: текущий каталог VFS и история команд."""

    cwd: list[str] = field(default_factory=list)
    history: list[str] = field(default_factory=list)


def count_nodes(node: VFSNode) -> tuple[int, int]:
    """Считает файлы и каталоги в поддереве, не включая сам узел."""
    files = dirs = 0
    for child in node.children.values():
        if child.is_directory:
            sub_files, sub_dirs = count_nodes(child)
            files += sub_files
            dirs += sub_dirs + 1
        else:
            files += 1
    return files, dirs


vfs = VirtualFileSystem.empty()
state = ShellState()


def virtual_cwd() -> str:
    """Возвращает текущий каталог VFS в виде абсолютного пути."""
    return "/" + "/".join(state.cwd)


def parse_ls_args(args):
    """Разбирает аргументы ls: признак -l и список путей."""
    long_format = False
    paths = []
    for arg in args:
        if arg == "-l":
            long_format = True
        elif arg.startswith("-") and arg != "-":
            raise CommandError(f"неизвестная опция: {arg}")
        else:
            paths.append(arg)
    return long_format, paths or ["."]


def format_entry(node: VFSNode, long_format: bool) -> str:
    """Форматирует строку вывода ls для узла VFS."""
    name = node.name + ("/" if node.is_directory else "")
    if not long_format:
        return name
    kind = "d" if node.is_directory else "-"
    size = 0 if node.is_directory else len(node.content)
    return f"{kind} {size:>8} {name}"


def list_path(path: str, long_format: bool):
    """Печатает содержимое каталога или сведения о файле."""
    node, _ = vfs.resolve(path, state.cwd)
    if not node.is_directory:
        print(format_entry(node, long_format))
        return
    for child in node.children.values():
        print(format_entry(child, long_format))


def cmd_ls(args):
    """Выводит содержимое каталогов VFS; поддерживает опцию -l."""
    long_format, paths = parse_ls_args(args)
    show_header = bool(paths[1:])
    for index, path in enumerate(paths):
        if index:
            print()
        if show_header:
            print(f"{path}:")
        try:
            list_path(path, long_format)
        except CommandError as error:
            print(f"ls: {path}: {error}", file=sys.stderr)


def cmd_cd(args):
    """Меняет текущий каталог VFS; без аргумента переходит в корень."""
    if args[1:]:
        raise CommandError("слишком много аргументов")
    target = args[0] if args else "/"
    node, parts = vfs.resolve(target, state.cwd)
    if not node.is_directory:
        raise CommandError(f"не является каталогом: {target}")
    state.cwd = parts


def cmd_echo(args):
    """Выводит аргументы, объединенные пробелами."""
    print(" ".join(args))


def cmd_whoami(args):
    """Выводит имя текущего пользователя реальной ОС."""
    if args:
        raise CommandError("лишние аргументы")
    print(get_username())


def cmd_history(args):
    """Выводит пронумерованную историю введенных команд."""
    if args:
        raise CommandError("лишние аргументы")
    for number, line in enumerate(state.history, start=1):
        print(f"{number:>5}  {line}")


def parse_tail_args(args):
    """Разбирает аргументы tail: число строк и список файлов."""
    if args[:1] != ["-n"]:
        return TAIL_DEFAULT_LINES, list(args)
    if not args[1:]:
        raise CommandError("опция -n требует число строк")
    try:
        count = int(args[1])
    except ValueError:
        raise CommandError(f"недопустимое число строк: {args[1]}") from None
    if count < 0:
        raise CommandError(f"недопустимое число строк: {args[1]}")
    return count, args[2:]


def read_vfs_text(path: str) -> str:
    """Читает файл VFS как текст UTF-8."""
    node, _ = vfs.resolve(path, state.cwd)
    if node.is_directory:
        raise CommandError("является каталогом")
    return node.content.decode("utf-8", errors="replace")


def cmd_tail(args):
    """Выводит последние строки файлов VFS (по умолчанию 10)."""
    count, files = parse_tail_args(args)
    if not files:
        raise CommandError("не указан файл")
    show_header = bool(files[1:])
    for index, path in enumerate(files):
        try:
            lines = read_vfs_text(path).splitlines()
        except CommandError as error:
            print(f"tail: {path}: {error}", file=sys.stderr)
            continue
        if index and show_header:
            print()
        if show_header:
            print(f"==> {path} <==")
        for line in lines[max(len(lines) - count, 0):]:
            print(line)


def cmd_vfs_info(args):
    """Служебная команда: показывает источник и размер загруженной VFS."""
    files, dirs = count_nodes(vfs.root)
    source = vfs.source_path or "(пустая VFS)"
    print(f"vfs-info: источник: {source}")
    print(f"vfs-info: файлов: {files}, каталогов: {dirs}")


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "echo": cmd_echo,
    "whoami": cmd_whoami,
    "history": cmd_history,
    "tail": cmd_tail,
    "vfs-info": cmd_vfs_info,
}


def execute_line(line: str, source: str = "") -> bool:
    """Выполняет команду и возвращает False для команды exit."""
    if line.strip():
        state.history.append(line.strip())
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

    global vfs, state
    state = ShellState()
    vfs = VirtualFileSystem.empty()
    if args.vfs_path:
        try:
            vfs = VirtualFileSystem.load(args.vfs_path)
        except VFSLoadError as error:
            print(f"Ошибка загрузки VFS: {error}", file=sys.stderr)
            return 1
        print(f"VFS загружена из: {vfs.source_path}")

    if args.startup_script and not run_startup_script(args.startup_script):
        return 0
    repl()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
