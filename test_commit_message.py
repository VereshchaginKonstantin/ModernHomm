#!/usr/bin/env python3
"""
Тесты для получения сообщения коммита
"""

import subprocess
import pytest


def test_git_available():
    """Проверка, что git доступен"""
    result = subprocess.run(['which', 'git'], capture_output=True, text=True)
    assert result.returncode == 0, "Git должен быть установлен"


def test_get_commit_message():
    """Проверка получения сообщения последнего коммита"""
    result = subprocess.run(
        ['git', 'log', '-1', '--pretty=%B'],
        capture_output=True,
        text=True,
        timeout=5
    )
    assert result.returncode == 0, "Команда git log должна выполниться успешно"
    assert len(result.stdout.strip()) > 0, "Сообщение коммита не должно быть пустым"


def test_commit_message_format():
    """Проверка формата сообщения коммита"""
    result = subprocess.run(
        ['git', 'log', '-1', '--pretty=%B'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0:
        full_message = result.stdout.strip()

        # Фильтруем строки
        lines = []
        for line in full_message.split('\n'):
            if '🤖 Generated with' not in line and 'Co-Authored-By:' not in line:
                lines.append(line)

        # Убираем пустые строки в конце
        while lines and not lines[-1].strip():
            lines.pop()

        filtered_message = '\n'.join(lines).strip()

        # Проверяем, что после фильтрации сообщение не пустое
        assert len(filtered_message) > 0, "Отфильтрованное сообщение не должно быть пустым"

        # Проверяем, что строки с автогенерацией удалены
        assert '🤖 Generated with' not in filtered_message
        assert 'Co-Authored-By:' not in filtered_message


def test_commit_subject_not_empty():
    """Проверка, что тема коммита не пустая"""
    result = subprocess.run(
        ['git', 'log', '-1', '--pretty=%s'],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode == 0:
        subject = result.stdout.strip()
        assert len(subject) > 0, "Тема коммита не должна быть пустой"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
