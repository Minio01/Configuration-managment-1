import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src.main import (
    build_argument_parser,
    cmd_cd,
    cmd_ls,
    cmd_vfs_info,
    count_nodes,
    main,
    parse_line,
    repl,
    run_startup_script,
    VFSLoadError,
    VirtualFileSystem,
)


class ShellParserTests(unittest.TestCase):
    def test_parse_line_splits_by_whitespace_and_preserves_quoted_strings(self):
        self.assertEqual(
            parse_line('ls "hello world"'), ['ls', 'hello world']
        )
        self.assertEqual(parse_line('ls -l /tmp'), ['ls', '-l', '/tmp'])

    def test_parse_line_handles_unclosed_quote(self):
        self.assertIsNone(parse_line('ls "unterminated'))

    def test_ls_and_cd_print_arguments(self):
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_ls(['-l', '/tmp'])
            cmd_cd(['..'])
        text = out.getvalue()
        self.assertIn('ls: команда вызвана с аргументами:', text)
        self.assertIn("['-l', '/tmp']", text)
        self.assertIn('cd: команда вызвана с аргументами:', text)
        self.assertIn("['..']", text)

    def test_repl_exits_on_exit(self):
        captured = io.StringIO()
        with patch('builtins.input', return_value='exit'):
            with redirect_stdout(captured):
                repl()
        self.assertIn('Выход.', captured.getvalue())

    def test_argument_parser_accepts_both_configuration_paths(self):
        args = build_argument_parser().parse_args([
            '--vfs-path', 'vfs', '--startup-script', 'startup.txt'
        ])
        self.assertEqual(args.vfs_path, 'vfs')
        self.assertEqual(args.startup_script, 'startup.txt')

    def test_startup_script_reports_error_and_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / 'startup.txt'
            script_path.write_text(
                'unknown_command\nls after-error\nexit\n', encoding='utf-8'
            )
            output = io.StringIO()
            errors = io.StringIO()
            with patch('src.main.get_prompt', return_value='user@host:~$ '):
                with redirect_stdout(output), redirect_stderr(errors):
                    should_start_repl = run_startup_script(str(script_path))

        self.assertFalse(should_start_repl)
        self.assertIn('user@host:~$ unknown_command', output.getvalue())
        self.assertIn('user@host:~$ ls after-error', output.getvalue())
        self.assertIn('after-error', output.getvalue())
        self.assertIn('Ошибка в стартовом скрипте', errors.getvalue())

    def test_vfs_loads_nested_files_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            nested = source / 'level1' / 'level2' / 'level3'
            nested.mkdir(parents=True)
            original = nested / 'data.txt'
            original.write_bytes(b'unchanged content')

            filesystem = VirtualFileSystem.load(str(source))
            node, parts = filesystem.resolve('/level1/level2/level3/data.txt')

            self.assertFalse(node.is_directory)
            self.assertEqual(parts, ['level1', 'level2', 'level3', 'data.txt'])
            self.assertEqual(node.content, b'unchanged content')
            self.assertEqual(original.read_bytes(), b'unchanged content')

    def test_vfs_resolves_relative_paths_and_parent_segments(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            (source / 'folder').mkdir(parents=True)
            (source / 'item.txt').write_text('item', encoding='utf-8')
            filesystem = VirtualFileSystem.load(str(source))

            node, parts = filesystem.resolve('../item.txt', ['folder'])

        self.assertFalse(node.is_directory)
        self.assertEqual(parts, ['item.txt'])

    def test_vfs_rejects_missing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / 'missing'
            with self.assertRaisesRegex(VFSLoadError, 'путь не найден'):
                VirtualFileSystem.load(str(missing_path))

    def test_vfs_rejects_file_as_source_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / 'not-a-directory'
            file_path.write_text('not a VFS directory', encoding='utf-8')
            with self.assertRaisesRegex(VFSLoadError, 'ожидалась директория'):
                VirtualFileSystem.load(str(file_path))

    def test_main_prints_parameters_and_runs_startup_script(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / 'startup.txt'
            vfs_path = Path(directory) / 'vfs'
            vfs_path.mkdir()
            script_path.write_text('exit\n', encoding='utf-8')
            output = io.StringIO()
            with redirect_stdout(output):
                main([
                    '--vfs-path', str(vfs_path), '--startup-script',
                    str(script_path)
                ])

        self.assertIn(f'Путь к VFS: {vfs_path}', output.getvalue())
        self.assertIn(f'Стартовый скрипт: {script_path}', output.getvalue())
        self.assertIn('VFS загружена из:', output.getvalue())
        self.assertIn('Выход.', output.getvalue())

    def test_vfs_info_counts_files_and_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            (source / 'a' / 'b').mkdir(parents=True)
            (source / 'a' / 'b' / 'one.txt').write_text('1', encoding='utf-8')
            (source / 'two.txt').write_text('2', encoding='utf-8')
            filesystem = VirtualFileSystem.load(str(source))
            self.assertEqual(count_nodes(filesystem.root), (2, 2))

            output = io.StringIO()
            with patch('src.main.vfs', filesystem):
                with redirect_stdout(output):
                    cmd_vfs_info([])
        self.assertIn('файлов: 2, каталогов: 2', output.getvalue())

    def test_main_reports_invalid_vfs_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid_path = Path(directory) / 'missing'
            output = io.StringIO()
            errors = io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(['--vfs-path', str(invalid_path)])

        self.assertEqual(result, 1)
        self.assertIn('Ошибка загрузки VFS', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
