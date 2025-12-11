using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;

namespace ModernHomm.UI
{
    /// <summary>
    /// UI для отображения лога игры
    /// </summary>
    public class GameLogUI : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Transform logContainer;
        [SerializeField] private GameObject logEntryPrefab;
        [SerializeField] private ScrollRect scrollRect;

        [Header("Settings")]
        [SerializeField] private int maxLogEntries = 50;
        [SerializeField] private bool autoScrollToBottom = true;

        private List<GameObject> _logEntries = new List<GameObject>();
        private int _lastLogCount = 0;

        public void UpdateLogs(List<LogEntry> logs)
        {
            if (logs == null) return;

            // Добавить только новые записи
            int newCount = logs.Count - _lastLogCount;
            if (newCount <= 0) return;

            // Добавить новые записи (в обратном порядке, чтобы новые были сверху)
            for (int i = logs.Count - newCount; i < logs.Count; i++)
            {
                AddLogEntry(logs[i]);
            }

            _lastLogCount = logs.Count;

            // Удалить старые записи если превышен лимит
            while (_logEntries.Count > maxLogEntries)
            {
                var oldest = _logEntries[_logEntries.Count - 1];
                _logEntries.RemoveAt(_logEntries.Count - 1);
                Destroy(oldest);
            }

            // Прокрутить к началу (новые записи)
            if (autoScrollToBottom && scrollRect != null)
            {
                Canvas.ForceUpdateCanvases();
                scrollRect.verticalNormalizedPosition = 1f;
            }
        }

        public void ClearLogs()
        {
            foreach (var entry in _logEntries)
            {
                if (entry != null) Destroy(entry);
            }
            _logEntries.Clear();
            _lastLogCount = 0;
        }

        private void AddLogEntry(LogEntry log)
        {
            if (logContainer == null || logEntryPrefab == null) return;

            GameObject entry = Instantiate(logEntryPrefab, logContainer);

            // Вставить в начало списка (новые сверху)
            entry.transform.SetAsFirstSibling();
            _logEntries.Insert(0, entry);

            // Найти текстовый компонент
            TextMeshProUGUI text = entry.GetComponentInChildren<TextMeshProUGUI>();
            if (text != null)
            {
                string icon = GetEventIcon(log.event_type);
                string message = FormatMessage(log.message);
                text.text = $"{icon} {message}";

                // Цвет в зависимости от типа события
                text.color = GetEventColor(log.event_type);
            }
        }

        private string GetEventIcon(string eventType)
        {
            switch (eventType?.ToLower())
            {
                case "attack":
                    return "⚔️";
                case "move":
                    return "🚶";
                case "game_started":
                    return "🎮";
                case "game_ended":
                    return "🏁";
                case "turn_switch":
                    return "🔄";
                case "skip":
                    return "⏭️";
                case "defer":
                    return "⏸️";
                default:
                    return "📝";
            }
        }

        private Color GetEventColor(string eventType)
        {
            switch (eventType?.ToLower())
            {
                case "attack":
                    return new Color(0.9f, 0.3f, 0.3f); // Красный
                case "move":
                    return new Color(0.3f, 0.7f, 0.3f); // Зелёный
                case "game_started":
                    return new Color(0.3f, 0.5f, 0.9f); // Синий
                case "game_ended":
                    return new Color(0.9f, 0.8f, 0.2f); // Жёлтый
                default:
                    return Color.white;
            }
        }

        private string FormatMessage(string message)
        {
            if (string.IsNullOrEmpty(message)) return "";

            // Ограничить длину сообщения
            if (message.Length > 100)
            {
                message = message.Substring(0, 97) + "...";
            }

            return message;
        }
    }
}
