import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.main import cmd_cd, cmd_echo, cmd_ls, parse_line, repl


class ShellParserTests(unittest.TestCase):
    def test_parse_line_splits_by_whitespace_and_preserves_quoted_strings(self):
        self.assertEqual(
            parse_line('echo "hello world"'), ['echo', 'hello world']
        )
        self.assertEqual(parse_line('ls -l /tmp'), ['ls', '-l', '/tmp'])

    def test_parse_line_handles_unclosed_quote(self):
        self.assertIsNone(parse_line('echo "unterminated'))

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

    def test_echo_prints_joined_arguments(self):
        out = io.StringIO()
        with redirect_stdout(out):
            cmd_echo(['hello', 'world'])
        self.assertEqual(out.getvalue(), 'hello world\n')

    def test_repl_exits_on_exit(self):
        captured = io.StringIO()
        with patch('builtins.input', return_value='exit'):
            with redirect_stdout(captured):
                repl()
        self.assertIn('Выход.', captured.getvalue())


if __name__ == '__main__':
    unittest.main()