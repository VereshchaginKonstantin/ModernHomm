using System;
using System.Runtime.InteropServices;
using UnityEngine;

namespace ModernHomm.Utils
{
    /// <summary>
    /// Мост для взаимодействия с браузером в WebGL билде
    /// </summary>
    public static class WebGLBridge
    {
        #if UNITY_WEBGL && !UNITY_EDITOR
        // URL Parameters & Storage
        [DllImport("__Internal")]
        private static extern string GetUrlParam(string paramName);

        [DllImport("__Internal")]
        private static extern void SetLocalStorage(string key, string value);

        [DllImport("__Internal")]
        private static extern string GetLocalStorage(string key);

        [DllImport("__Internal")]
        private static extern void RemoveLocalStorage(string key);

        [DllImport("__Internal")]
        private static extern string GetCurrentUrl();

        [DllImport("__Internal")]
        private static extern void RedirectTo(string url);

        // UI Functions
        [DllImport("__Internal")]
        private static extern void JS_UpdateTurnIndicator(string text, bool isMyTurn);

        [DllImport("__Internal")]
        private static extern void JS_UpdateHint(string text);

        [DllImport("__Internal")]
        private static extern void JS_UpdatePlayer1Info(string name, string stats);

        [DllImport("__Internal")]
        private static extern void JS_UpdatePlayer2Info(string name, string stats);

        [DllImport("__Internal")]
        private static extern void JS_SetPlayerActive(int playerNum);

        [DllImport("__Internal")]
        private static extern void JS_EnableActionButtons(bool canMove, bool canAttack, bool canSkip, bool canDefer);

        [DllImport("__Internal")]
        private static extern void JS_DisableAllActionButtons();

        [DllImport("__Internal")]
        private static extern void JS_AddLogEntry(string message, string type);

        [DllImport("__Internal")]
        private static extern void JS_ClearLog();

        [DllImport("__Internal")]
        private static extern void JS_ShowBattleOverlay(string attackerName, string attackerImage, string targetName, string targetImage, string resultText);

        [DllImport("__Internal")]
        private static extern void JS_CloseBattleOverlay();

        [DllImport("__Internal")]
        private static extern void JS_ShowGameOver(bool isWinner, string winnerName);
        #endif

        #region URL & Storage

        /// <summary>
        /// Получить параметр из URL (?param=value)
        /// </summary>
        public static string GetUrlParameter(string paramName)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                return GetUrlParam(paramName);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to get URL param '{paramName}': {e.Message}");
                return null;
            }
            #else
            // В редакторе возвращаем null или тестовые значения
            return null;
            #endif
        }

        /// <summary>
        /// Сохранить значение в localStorage
        /// </summary>
        public static void SaveToLocalStorage(string key, string value)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                SetLocalStorage(key, value);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to save to localStorage: {e.Message}");
            }
            #else
            PlayerPrefs.SetString(key, value);
            PlayerPrefs.Save();
            #endif
        }

        /// <summary>
        /// Загрузить значение из localStorage
        /// </summary>
        public static string LoadFromLocalStorage(string key)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                return GetLocalStorage(key);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to load from localStorage: {e.Message}");
                return null;
            }
            #else
            return PlayerPrefs.GetString(key, null);
            #endif
        }

        /// <summary>
        /// Удалить значение из localStorage
        /// </summary>
        public static void DeleteFromLocalStorage(string key)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                RemoveLocalStorage(key);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to delete from localStorage: {e.Message}");
            }
            #else
            PlayerPrefs.DeleteKey(key);
            PlayerPrefs.Save();
            #endif
        }

        /// <summary>
        /// Получить текущий URL страницы
        /// </summary>
        public static string GetPageUrl()
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                return GetCurrentUrl();
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to get current URL: {e.Message}");
                return Application.absoluteURL;
            }
            #else
            return "http://localhost";
            #endif
        }

        /// <summary>
        /// Перенаправить на другой URL
        /// </summary>
        public static void Redirect(string url)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                RedirectTo(url);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to redirect: {e.Message}");
                Application.OpenURL(url);
            }
            #else
            Application.OpenURL(url);
            #endif
        }

        /// <summary>
        /// Получить ID игрока из URL или localStorage
        /// </summary>
        public static int? GetPlayerId()
        {
            // Сначала пробуем из URL
            string playerIdStr = GetUrlParameter("player_id");
            if (!string.IsNullOrEmpty(playerIdStr) && int.TryParse(playerIdStr, out int playerId))
            {
                // Сохранить в localStorage для следующего раза
                SaveToLocalStorage("player_id", playerIdStr);
                return playerId;
            }

            // Потом из localStorage
            playerIdStr = LoadFromLocalStorage("player_id");
            if (!string.IsNullOrEmpty(playerIdStr) && int.TryParse(playerIdStr, out playerId))
            {
                return playerId;
            }

            return null;
        }

        /// <summary>
        /// Получить ID игры из URL
        /// </summary>
        public static int? GetGameId()
        {
            string gameIdStr = GetUrlParameter("game_id");
            if (!string.IsNullOrEmpty(gameIdStr) && int.TryParse(gameIdStr, out int gameId))
            {
                return gameId;
            }
            return null;
        }

        /// <summary>
        /// Сохранить ID игрока
        /// </summary>
        public static void SavePlayerId(int playerId)
        {
            SaveToLocalStorage("player_id", playerId.ToString());
        }

        /// <summary>
        /// Очистить сессию
        /// </summary>
        public static void ClearSession()
        {
            DeleteFromLocalStorage("player_id");
        }

        #endregion

        #region UI Updates

        /// <summary>
        /// Обновить индикатор хода
        /// </summary>
        public static void UpdateTurnIndicator(string text, bool isMyTurn)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_UpdateTurnIndicator(text, isMyTurn);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to update turn indicator: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Turn Indicator: {text} (isMyTurn: {isMyTurn})");
            #endif
        }

        /// <summary>
        /// Обновить подсказку
        /// </summary>
        public static void UpdateHint(string text)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_UpdateHint(text);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to update hint: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Hint: {text}");
            #endif
        }

        /// <summary>
        /// Обновить информацию игрока 1
        /// </summary>
        public static void UpdatePlayer1Info(string name, string stats)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_UpdatePlayer1Info(name, stats);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to update player 1 info: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Player1: {name} - {stats}");
            #endif
        }

        /// <summary>
        /// Обновить информацию игрока 2
        /// </summary>
        public static void UpdatePlayer2Info(string name, string stats)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_UpdatePlayer2Info(name, stats);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to update player 2 info: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Player2: {name} - {stats}");
            #endif
        }

        /// <summary>
        /// Установить активного игрока (1 или 2)
        /// </summary>
        public static void SetPlayerActive(int playerNum)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_SetPlayerActive(playerNum);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to set player active: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Active player: {playerNum}");
            #endif
        }

        /// <summary>
        /// Включить/выключить кнопки действий
        /// </summary>
        public static void EnableActionButtons(bool canMove, bool canAttack, bool canSkip, bool canDefer)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_EnableActionButtons(canMove, canAttack, canSkip, canDefer);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to enable action buttons: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Action buttons - Move:{canMove}, Attack:{canAttack}, Skip:{canSkip}, Defer:{canDefer}");
            #endif
        }

        /// <summary>
        /// Отключить все кнопки действий
        /// </summary>
        public static void DisableAllActionButtons()
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_DisableAllActionButtons();
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to disable action buttons: {e.Message}");
            }
            #else
            Debug.Log("[UI] All action buttons disabled");
            #endif
        }

        /// <summary>
        /// Добавить запись в лог
        /// </summary>
        public static void AddLogEntry(string message, string type = "info")
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_AddLogEntry(message, type);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to add log entry: {e.Message}");
            }
            #else
            Debug.Log($"[LOG] [{type}] {message}");
            #endif
        }

        /// <summary>
        /// Очистить лог
        /// </summary>
        public static void ClearLog()
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_ClearLog();
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to clear log: {e.Message}");
            }
            #else
            Debug.Log("[UI] Log cleared");
            #endif
        }

        #endregion

        #region Overlays

        /// <summary>
        /// Показать оверлей битвы
        /// </summary>
        public static void ShowBattleOverlay(string attackerName, string attackerImage, string targetName, string targetImage, string resultText)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_ShowBattleOverlay(attackerName, attackerImage, targetName, targetImage, resultText);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to show battle overlay: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Battle: {attackerName} vs {targetName} - {resultText}");
            #endif
        }

        /// <summary>
        /// Закрыть оверлей битвы
        /// </summary>
        public static void CloseBattleOverlay()
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_CloseBattleOverlay();
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to close battle overlay: {e.Message}");
            }
            #else
            Debug.Log("[UI] Battle overlay closed");
            #endif
        }

        /// <summary>
        /// Показать оверлей окончания игры
        /// </summary>
        public static void ShowGameOver(bool isWinner, string winnerName)
        {
            #if UNITY_WEBGL && !UNITY_EDITOR
            try
            {
                JS_ShowGameOver(isWinner, winnerName);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[WebGL] Failed to show game over: {e.Message}");
            }
            #else
            Debug.Log($"[UI] Game Over - Winner: {winnerName}, You won: {isWinner}");
            #endif
        }

        #endregion
    }
}
