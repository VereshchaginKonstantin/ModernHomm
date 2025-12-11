using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace ModernHomm.Core
{
    /// <summary>
    /// HTTP клиент для взаимодействия с API арены
    /// </summary>
    public class ApiClient : MonoBehaviour
    {
        private static ApiClient _instance;
        public static ApiClient Instance
        {
            get
            {
                if (_instance == null)
                {
                    var go = new GameObject("ApiClient");
                    _instance = go.AddComponent<ApiClient>();
                    DontDestroyOnLoad(go);
                }
                return _instance;
            }
        }

        // Базовый URL API (настраивается в зависимости от окружения)
        private string _baseUrl = "";

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }
            _instance = this;
            DontDestroyOnLoad(gameObject);

            // Определяем базовый URL в зависимости от окружения
            #if UNITY_EDITOR
            _baseUrl = "http://localhost:5000";
            #else
            // В WebGL используем относительный путь или получаем из URL
            _baseUrl = GetBaseUrlFromBrowser();
            #endif
        }

        private string GetBaseUrlFromBrowser()
        {
            // В WebGL билде получаем базовый URL из браузера
            #if UNITY_WEBGL && !UNITY_EDITOR
            string url = Application.absoluteURL;
            if (!string.IsNullOrEmpty(url))
            {
                Uri uri = new Uri(url);
                return $"{uri.Scheme}://{uri.Host}:{uri.Port}";
            }
            #endif
            return "http://modernhomm.ru";
        }

        public void SetBaseUrl(string url)
        {
            _baseUrl = url;
        }

        #region API Methods

        /// <summary>
        /// Получить список игроков
        /// </summary>
        public void GetPlayers(Action<PlayersListResponse> onSuccess, Action<string> onError)
        {
            StartCoroutine(GetRequest<PlayersListResponse>(
                "/arena/api/players",
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Получить ожидающие игры для игрока
        /// </summary>
        public void GetPendingGames(int playerId, Action<PendingGamesResponse> onSuccess, Action<string> onError)
        {
            StartCoroutine(GetRequest<PendingGamesResponse>(
                $"/arena/api/games/pending?player_id={playerId}",
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Создать новую игру
        /// </summary>
        public void CreateGame(int player1Id, string player2Name, string fieldSize,
            Action<CreateGameResponse> onSuccess, Action<string> onError)
        {
            var request = new CreateGameRequest
            {
                player1_id = player1Id,
                player2_name = player2Name,
                field_size = fieldSize
            };
            StartCoroutine(PostRequest<CreateGameRequest, CreateGameResponse>(
                "/arena/api/games/create",
                request,
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Принять игру
        /// </summary>
        public void AcceptGame(int gameId, int playerId, Action<CreateGameResponse> onSuccess, Action<string> onError)
        {
            var request = new AcceptGameRequest { player_id = playerId };
            StartCoroutine(PostRequest<AcceptGameRequest, CreateGameResponse>(
                $"/arena/api/games/{gameId}/accept",
                request,
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Отклонить игру
        /// </summary>
        public void DeclineGame(int gameId, int playerId, Action<CreateGameResponse> onSuccess, Action<string> onError)
        {
            var request = new AcceptGameRequest { player_id = playerId };
            StartCoroutine(PostRequest<AcceptGameRequest, CreateGameResponse>(
                $"/arena/api/games/{gameId}/decline",
                request,
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Получить состояние игры
        /// </summary>
        public void GetGameState(int gameId, Action<GameStateResponse> onSuccess, Action<string> onError)
        {
            StartCoroutine(GetRequest<GameStateResponse>(
                $"/arena/api/games/{gameId}/state",
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Получить доступные действия юнита
        /// </summary>
        public void GetUnitActions(int gameId, int unitId, Action<UnitActionsResponse> onSuccess, Action<string> onError)
        {
            StartCoroutine(GetRequest<UnitActionsResponse>(
                $"/arena/api/games/{gameId}/units/{unitId}/actions",
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Выполнить движение юнита
        /// </summary>
        public void MoveUnit(int gameId, int unitId, int targetX, int targetY,
            Action<MoveResponse> onSuccess, Action<string> onError)
        {
            var request = new MoveRequest
            {
                unit_id = unitId,
                action = "move",
                target_x = targetX,
                target_y = targetY
            };
            StartCoroutine(PostRequest<MoveRequest, MoveResponse>(
                $"/arena/api/games/{gameId}/move",
                request,
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Выполнить атаку юнитом
        /// </summary>
        public void AttackUnit(int gameId, int unitId, int targetUnitId,
            Action<MoveResponse> onSuccess, Action<string> onError)
        {
            var request = new MoveRequest
            {
                unit_id = unitId,
                action = "attack",
                target_unit_id = targetUnitId
            };
            StartCoroutine(PostRequest<MoveRequest, MoveResponse>(
                $"/arena/api/games/{gameId}/move",
                request,
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Пропустить ход юнита
        /// </summary>
        public void SkipUnit(int gameId, int unitId, Action<MoveResponse> onSuccess, Action<string> onError)
        {
            var request = new MoveRequest
            {
                unit_id = unitId,
                action = "skip"
            };
            StartCoroutine(PostRequest<MoveRequest, MoveResponse>(
                $"/arena/api/games/{gameId}/move",
                request,
                onSuccess,
                onError
            ));
        }

        /// <summary>
        /// Отложить ход юнита
        /// </summary>
        public void DeferUnit(int gameId, int unitId, Action<MoveResponse> onSuccess, Action<string> onError)
        {
            var request = new MoveRequest
            {
                unit_id = unitId,
                action = "defer"
            };
            StartCoroutine(PostRequest<MoveRequest, MoveResponse>(
                $"/arena/api/games/{gameId}/move",
                request,
                onSuccess,
                onError
            ));
        }

        #endregion

        #region HTTP Helpers

        private IEnumerator GetRequest<TResponse>(string endpoint, Action<TResponse> onSuccess, Action<string> onError)
        {
            string url = _baseUrl + endpoint;
            Debug.Log($"[API] GET {url}");

            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Accept", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        string json = request.downloadHandler.text;
                        Debug.Log($"[API] Response: {json.Substring(0, Math.Min(500, json.Length))}...");
                        TResponse response = JsonUtility.FromJson<TResponse>(json);
                        onSuccess?.Invoke(response);
                    }
                    catch (Exception e)
                    {
                        onError?.Invoke($"Parse error: {e.Message}");
                    }
                }
                else
                {
                    onError?.Invoke($"HTTP Error: {request.error}");
                }
            }
        }

        private IEnumerator PostRequest<TRequest, TResponse>(string endpoint, TRequest data,
            Action<TResponse> onSuccess, Action<string> onError)
        {
            string url = _baseUrl + endpoint;
            string jsonData = JsonUtility.ToJson(data);
            Debug.Log($"[API] POST {url}: {jsonData}");

            using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Accept", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        string json = request.downloadHandler.text;
                        Debug.Log($"[API] Response: {json}");
                        TResponse response = JsonUtility.FromJson<TResponse>(json);
                        onSuccess?.Invoke(response);
                    }
                    catch (Exception e)
                    {
                        onError?.Invoke($"Parse error: {e.Message}");
                    }
                }
                else
                {
                    string errorBody = request.downloadHandler?.text ?? "";
                    onError?.Invoke($"HTTP Error: {request.error}. Body: {errorBody}");
                }
            }
        }

        #endregion
    }
}
