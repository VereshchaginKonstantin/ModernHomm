using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;

namespace ModernHomm.UI
{
    /// <summary>
    /// UI для выбора противника и создания игры
    /// </summary>
    public class PlayerSelectUI : MonoBehaviour
    {
        [Header("Current Player Info")]
        [SerializeField] private TextMeshProUGUI playerNameText;
        [SerializeField] private TextMeshProUGUI playerBalanceText;
        [SerializeField] private TextMeshProUGUI playerArmyCostText;
        [SerializeField] private TextMeshProUGUI playerStatsText;

        [Header("Opponent Selection")]
        [SerializeField] private TMP_Dropdown opponentDropdown;
        [SerializeField] private TextMeshProUGUI opponentInfoText;

        [Header("Field Selection")]
        [SerializeField] private TMP_Dropdown fieldSizeDropdown;

        [Header("Actions")]
        [SerializeField] private Button startBattleButton;
        [SerializeField] private TextMeshProUGUI statusText;

        [Header("Pending Game Panel")]
        [SerializeField] private GameObject pendingGamePanel;
        [SerializeField] private TextMeshProUGUI pendingGameText;
        [SerializeField] private Button acceptButton;
        [SerializeField] private Button declineButton;

        [Header("Settings")]
        [SerializeField] private float armyCostFilterPercent = 0.5f; // ±50%

        // Данные
        private List<PlayerInfo> _players = new List<PlayerInfo>();
        private List<PlayerInfo> _filteredPlayers = new List<PlayerInfo>();
        private PlayerInfo _currentPlayer;
        private PendingGame _pendingGame;

        private readonly string[] _fieldSizes = { "5x5", "7x7", "10x10" };

        private void Start()
        {
            // Настроить UI
            SetupDropdowns();
            SetupButtons();

            // Загрузить данные
            LoadPlayers();
        }

        private void SetupDropdowns()
        {
            // Размеры поля
            if (fieldSizeDropdown != null)
            {
                fieldSizeDropdown.ClearOptions();
                fieldSizeDropdown.AddOptions(new List<string>(_fieldSizes));
                fieldSizeDropdown.value = 0;
            }

            // Противники
            if (opponentDropdown != null)
            {
                opponentDropdown.onValueChanged.AddListener(OnOpponentSelected);
            }
        }

        private void SetupButtons()
        {
            if (startBattleButton != null)
            {
                startBattleButton.onClick.AddListener(OnStartBattleClicked);
            }

            if (acceptButton != null)
            {
                acceptButton.onClick.AddListener(OnAcceptPendingGame);
            }

            if (declineButton != null)
            {
                declineButton.onClick.AddListener(OnDeclinePendingGame);
            }
        }

        #region Data Loading

        private void LoadPlayers()
        {
            SetStatus("Загрузка игроков...");

            ApiClient.Instance.GetPlayers(
                response =>
                {
                    _players = response.players;

                    // Найти текущего игрока (пока используем первого с юнитами)
                    // В реальном приложении ID игрока приходит из сессии/localStorage
                    _currentPlayer = _players.FirstOrDefault(p => p.units != null && p.units.Count > 0);

                    if (_currentPlayer != null)
                    {
                        GameManager.Instance.CurrentPlayerId = _currentPlayer.id;
                        UpdateCurrentPlayerInfo();
                        FilterOpponents();
                        CheckPendingGames();
                        SetStatus("");
                    }
                    else
                    {
                        SetStatus("У вас нет юнитов для боя!");
                    }
                },
                error =>
                {
                    SetStatus($"Ошибка: {error}");
                }
            );
        }

        private void CheckPendingGames()
        {
            if (_currentPlayer == null) return;

            ApiClient.Instance.GetPendingGames(_currentPlayer.id,
                response =>
                {
                    if (response.games != null && response.games.Count > 0)
                    {
                        ShowPendingGame(response.games[0]);
                    }
                    else
                    {
                        HidePendingGame();
                    }
                },
                error =>
                {
                    Debug.LogError($"Failed to check pending games: {error}");
                }
            );
        }

        #endregion

        #region UI Updates

        private void UpdateCurrentPlayerInfo()
        {
            if (_currentPlayer == null) return;

            if (playerNameText != null)
                playerNameText.text = $"👤 {_currentPlayer.name}";

            if (playerBalanceText != null)
                playerBalanceText.text = $"💰 {_currentPlayer.balance:N0}";

            if (playerArmyCostText != null)
                playerArmyCostText.text = $"⚔️ {_currentPlayer.army_cost:N0}";

            if (playerStatsText != null)
            {
                float winRate = _currentPlayer.wins + _currentPlayer.losses > 0
                    ? (float)_currentPlayer.wins / (_currentPlayer.wins + _currentPlayer.losses) * 100
                    : 0;
                playerStatsText.text = $"🏆 {_currentPlayer.wins} | 💔 {_currentPlayer.losses} ({winRate:N0}%)";
            }
        }

        private void FilterOpponents()
        {
            if (_currentPlayer == null) return;

            float minCost = _currentPlayer.army_cost * (1 - armyCostFilterPercent);
            float maxCost = _currentPlayer.army_cost * (1 + armyCostFilterPercent);

            _filteredPlayers = _players
                .Where(p => p.id != _currentPlayer.id &&
                           p.army_cost >= minCost &&
                           p.army_cost <= maxCost &&
                           p.units != null &&
                           p.units.Count > 0)
                .OrderBy(p => p.name)
                .ToList();

            UpdateOpponentDropdown();
        }

        private void UpdateOpponentDropdown()
        {
            if (opponentDropdown == null) return;

            opponentDropdown.ClearOptions();

            if (_filteredPlayers.Count == 0)
            {
                opponentDropdown.AddOptions(new List<string> { "Нет доступных противников" });
                startBattleButton.interactable = false;
                return;
            }

            List<string> options = _filteredPlayers.Select(p =>
            {
                float winRate = p.wins + p.losses > 0
                    ? (float)p.wins / (p.wins + p.losses) * 100
                    : 0;
                return $"{p.name} (⚔️{p.army_cost:N0} | {winRate:N0}%)";
            }).ToList();

            opponentDropdown.AddOptions(options);
            startBattleButton.interactable = true;

            OnOpponentSelected(0);
        }

        private void OnOpponentSelected(int index)
        {
            if (opponentInfoText == null || index >= _filteredPlayers.Count) return;

            PlayerInfo opponent = _filteredPlayers[index];

            string unitsInfo = "";
            if (opponent.units != null)
            {
                unitsInfo = string.Join(", ", opponent.units.Select(u => $"{u.unit_name} x{u.count}"));
            }

            opponentInfoText.text = $"Армия: {unitsInfo}\n" +
                                   $"Побед: {opponent.wins} | Поражений: {opponent.losses}";
        }

        private void ShowPendingGame(PendingGame game)
        {
            _pendingGame = game;

            if (pendingGamePanel != null)
            {
                pendingGamePanel.SetActive(true);

                if (pendingGameText != null)
                {
                    pendingGameText.text = $"⚔️ {game.player1_name} вызывает вас на бой!\n" +
                                          $"Поле: {game.field_size}";
                }
            }
        }

        private void HidePendingGame()
        {
            _pendingGame = null;

            if (pendingGamePanel != null)
            {
                pendingGamePanel.SetActive(false);
            }
        }

        private void SetStatus(string message)
        {
            if (statusText != null)
            {
                statusText.text = message;
            }
        }

        #endregion

        #region Button Handlers

        private void OnStartBattleClicked()
        {
            if (_currentPlayer == null || _filteredPlayers.Count == 0) return;

            int selectedIndex = opponentDropdown.value;
            if (selectedIndex >= _filteredPlayers.Count) return;

            PlayerInfo opponent = _filteredPlayers[selectedIndex];
            string fieldSize = _fieldSizes[fieldSizeDropdown.value];

            SetStatus("Создание игры...");
            startBattleButton.interactable = false;

            ApiClient.Instance.CreateGame(_currentPlayer.id, opponent.name, fieldSize,
                response =>
                {
                    if (response.success)
                    {
                        SetStatus($"Вызов отправлен! Ожидание ответа...");
                        // Можно перейти на экран ожидания или начать polling
                    }
                    else
                    {
                        SetStatus($"Ошибка: {response.message}");
                        startBattleButton.interactable = true;
                    }
                },
                error =>
                {
                    SetStatus($"Ошибка: {error}");
                    startBattleButton.interactable = true;
                }
            );
        }

        private void OnAcceptPendingGame()
        {
            if (_pendingGame == null || _currentPlayer == null) return;

            SetStatus("Принятие вызова...");
            acceptButton.interactable = false;
            declineButton.interactable = false;

            ApiClient.Instance.AcceptGame(_pendingGame.game_id, _currentPlayer.id,
                response =>
                {
                    if (response.success)
                    {
                        // Перейти к игре
                        GameManager.Instance.LoadBattleScene(_pendingGame.game_id);
                    }
                    else
                    {
                        SetStatus($"Ошибка: {response.message}");
                        acceptButton.interactable = true;
                        declineButton.interactable = true;
                    }
                },
                error =>
                {
                    SetStatus($"Ошибка: {error}");
                    acceptButton.interactable = true;
                    declineButton.interactable = true;
                }
            );
        }

        private void OnDeclinePendingGame()
        {
            if (_pendingGame == null || _currentPlayer == null) return;

            ApiClient.Instance.DeclineGame(_pendingGame.game_id, _currentPlayer.id,
                response =>
                {
                    HidePendingGame();
                    CheckPendingGames(); // Проверить другие вызовы
                },
                error =>
                {
                    Debug.LogError($"Failed to decline game: {error}");
                }
            );
        }

        #endregion
    }
}
