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
    main,
    parse_line,
    repl,
    run_startup_script,
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

    def test_main_prints_parameters_and_runs_startup_script(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / 'startup.txt'
            script_path.write_text('exit\n', encoding='utf-8')
            output = io.StringIO()
            with redirect_stdout(output):
                main([
                    '--vfs-path', 'vfs', '--startup-script', str(script_path)
                ])

        self.assertIn('Путь к VFS: vfs', output.getvalue())
        self.assertIn(f'Стартовый скрипт: {script_path}', output.getvalue())
        self.assertIn('Выход.', output.getvalue())


if __name__ == '__main__':
    unittest.main()
