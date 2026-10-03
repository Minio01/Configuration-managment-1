import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src import main as shell


class CommandTestCase(unittest.TestCase):
    """Базовый класс: подготавливает VFS во временном каталоге."""

    def prepare_environment(self):
        """Создает VFS во временном каталоге и подменяет состояние."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        source = Path(directory.name)
        (source / 'dir' / 'sub').mkdir(parents=True)
        (source / 'dir' / 'sub' / 'deep.txt').write_bytes(b'deep\n')
        (source / 'dir' / 'note.txt').write_bytes(b'note\n')
        (source / 'log.txt').write_bytes(
            ''.join(f'line {n}\n' for n in range(1, 16)).encode('utf-8')
        )
        loaded = shell.VirtualFileSystem.load(str(source))
        for name, value in (('vfs', loaded), ('state', shell.ShellState())):
            patcher = patch.object(shell, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
    def run_line(self, line):
        """Выполняет строку и возвращает вывод и сообщения об ошибках."""
        if not hasattr(self, 'prepared'):
            self.prepared = True
            self.prepare_environment()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            shell.execute_line(line)
        return out.getvalue(), err.getvalue()


class LsCdTests(CommandTestCase):
    def test_ls_lists_root_with_directory_markers(self):
        out, _ = self.run_line('ls')
        self.assertEqual(out, 'dir/\nlog.txt\n')

    def test_ls_long_format_shows_type_and_size(self):
        out, _ = self.run_line('ls -l dir')
        self.assertIn('d        0 sub/', out)
        self.assertIn('-        5 note.txt', out)

    def test_ls_reports_missing_path_and_unknown_option(self):
        _, err = self.run_line('ls missing')
        self.assertIn('путь не найден', err)
        _, err = self.run_line('ls -z')
        self.assertIn('неизвестная опция', err)

    def test_ls_of_file_prints_file_entry(self):
        out, _ = self.run_line('ls dir/note.txt')
        self.assertEqual(out, 'note.txt\n')

    def test_ls_multiple_paths_prints_headers(self):
        out, _ = self.run_line('ls dir dir/sub')
        self.assertIn('dir:\n', out)
        self.assertIn('dir/sub:\ndeep.txt\n', out)

    def test_cd_changes_directory_and_prompt(self):
        self.run_line('cd dir/sub')
        self.assertEqual(shell.virtual_cwd(), '/dir/sub')
        self.assertTrue(shell.get_prompt().endswith(':/dir/sub$ '))
        self.run_line('cd ..')
        self.assertEqual(shell.virtual_cwd(), '/dir')
        self.run_line('cd')
        self.assertEqual(shell.virtual_cwd(), '/')

    def test_cd_rejects_file_missing_path_and_extra_arguments(self):
        for line, text in (
            ('cd log.txt', 'не является каталогом'),
            ('cd nowhere', 'путь не найден'),
            ('cd a b', 'слишком много аргументов'),
        ):
            _, err = self.run_line(line)
            self.assertIn(text, err)
        self.assertEqual(shell.virtual_cwd(), '/')

    def test_relative_paths_use_current_directory(self):
        self.run_line('cd dir')
        out, _ = self.run_line('ls sub')
        self.assertEqual(out, 'deep.txt\n')


class OtherCommandTests(CommandTestCase):
    def test_whoami_prints_real_user(self):
        with patch.object(shell, 'get_username', return_value='alice'):
            out, _ = self.run_line('whoami')
        self.assertEqual(out, 'alice\n')

    def test_whoami_rejects_arguments(self):
        _, err = self.run_line('whoami x')
        self.assertIn('лишние аргументы', err)

    def test_history_lists_commands_with_numbers(self):
        self.run_line('echo one')
        self.run_line('unknown')
        out, _ = self.run_line('history')
        self.assertEqual(
            out, '    1  echo one\n    2  unknown\n    3  history\n'
        )

    def test_tail_defaults_to_ten_lines(self):
        out, _ = self.run_line('tail log.txt')
        self.assertEqual(out.splitlines(), [f'line {n}' for n in range(6, 16)])

    def test_tail_n_option(self):
        out, _ = self.run_line('tail -n 2 log.txt')
        self.assertEqual(out, 'line 14\nline 15\n')
        out, _ = self.run_line('tail -n 0 log.txt')
        self.assertEqual(out, '')

    def test_tail_multiple_files_prints_headers(self):
        out, _ = self.run_line('tail -n 1 log.txt dir/note.txt')
        self.assertEqual(
            out, '==> log.txt <==\nline 15\n\n==> dir/note.txt <==\nnote\n'
        )

    def test_tail_reports_errors(self):
        for line, text in (
            ('tail', 'не указан файл'),
            ('tail -n', 'требует число строк'),
            ('tail -n x log.txt', 'недопустимое число строк'),
            ('tail -n -1 log.txt', 'недопустимое число строк'),
            ('tail missing', 'путь не найден'),
            ('tail dir', 'является каталогом'),
        ):
            _, err = self.run_line(line)
            self.assertIn(text, err)


if __name__ == '__main__':
    unittest.main()