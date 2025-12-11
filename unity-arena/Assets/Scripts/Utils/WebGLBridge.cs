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
        #endif

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
            // В редакторе возвращаем null
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
    }
}
