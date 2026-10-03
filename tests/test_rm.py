import unittest
from pathlib import Path

from src import main as shell
from tests.test_commands import CommandTestCase


class RmTests(CommandTestCase):
    def test_rm_removes_file_from_memory_only(self):
        out, err = self.run_line('rm log.txt')
        self.assertEqual((out, err), ('', ''))
        out, _ = self.run_line('ls')
        self.assertEqual(out, 'dir/\n')
        self.assertTrue((shell.vfs.source_path / 'log.txt').exists())

    def test_rm_directory_requires_recursive_option(self):
        _, err = self.run_line('rm dir')
        self.assertIn('нужна опция -r', err)
        self.run_line('rm -r dir')
        out, _ = self.run_line('ls')
        self.assertEqual(out, 'log.txt\n')
        self.assertTrue(Path(shell.vfs.source_path / 'dir').is_dir())

    def test_rm_multiple_paths_and_combined_flags(self):
        self.run_line('rm -rf dir log.txt')
        out, _ = self.run_line('ls')
        self.assertEqual(out, '')

    def test_rm_missing_path_reports_error_unless_forced(self):
        _, err = self.run_line('rm missing')
        self.assertIn('путь не найден', err)
        _, err = self.run_line('rm -f missing')
        self.assertEqual(err, '')

    def test_rm_rejects_root_and_current_directory(self):
        _, err = self.run_line('rm -r /')
        self.assertIn('корневой каталог', err)
        self.run_line('cd dir/sub')
        _, err = self.run_line('rm -r /dir')
        self.assertIn('текущий каталог', err)
        out, _ = self.run_line('ls /dir')
        self.assertIn('sub/', out)

    def test_rm_rejects_bad_usage(self):
        _, err = self.run_line('rm')
        self.assertIn('не указан файл', err)
        _, err = self.run_line('rm -x log.txt')
        self.assertIn('неизвестная опция', err)


if __name__ == '__main__':
    unittest.main()
