using UnityEngine;
using UnityEngine.SceneManagement;

namespace ModernHomm.Core
{
    /// <summary>
    /// Инициализация игры при запуске
    /// Этот скрипт должен быть на первой сцене
    /// </summary>
    public class Bootstrap : MonoBehaviour
    {
        [Header("Settings")]
        [SerializeField] private string mainMenuSceneName = "MainMenu";
        [SerializeField] private bool autoLoadMainMenu = true;

        [Header("Debug")]
        [SerializeField] private bool enableDebugLogs = true;
        [SerializeField] private string debugApiUrl = "";

        private static bool _isInitialized = false;

        private void Awake()
        {
            if (_isInitialized)
            {
                Destroy(gameObject);
                return;
            }

            _isInitialized = true;
            DontDestroyOnLoad(gameObject);

            Initialize();
        }

        private void Initialize()
        {
            Debug.Log("[Bootstrap] Initializing game...");

            // Инициализация ApiClient
            var apiClient = ApiClient.Instance;
            if (!string.IsNullOrEmpty(debugApiUrl))
            {
                apiClient.SetBaseUrl(debugApiUrl);
            }

            // Инициализация GameManager
            var gameManager = GameManager.Instance;

            // Настройка логов
            if (!enableDebugLogs)
            {
                Debug.unityLogger.filterLogType = LogType.Warning;
            }

            Debug.Log("[Bootstrap] Game initialized successfully");

            // Загрузить главное меню
            if (autoLoadMainMenu && SceneManager.GetActiveScene().name != mainMenuSceneName)
            {
                SceneManager.LoadScene(mainMenuSceneName);
            }
        }

        /// <summary>
        /// Проверить, инициализирована ли игра
        /// </summary>
        public static bool IsInitialized => _isInitialized;
    }
}
