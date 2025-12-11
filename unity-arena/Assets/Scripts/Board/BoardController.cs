using System.Collections.Generic;
using UnityEngine;
using ModernHomm.Core;

namespace ModernHomm.Board
{
    /// <summary>
    /// Контроллер игрового поля - создание и управление сеткой
    /// </summary>
    public class BoardController : MonoBehaviour
    {
        [Header("Prefabs")]
        [SerializeField] private GameObject cellPrefab;
        [SerializeField] private GameObject unitPrefab;
        [SerializeField] private GameObject obstaclePrefab;

        [Header("Settings")]
        [SerializeField] private float cellSize = 1f;
        [SerializeField] private Color lightCellColor = new Color(0.9f, 0.9f, 0.85f);
        [SerializeField] private Color darkCellColor = new Color(0.6f, 0.6f, 0.55f);
        [SerializeField] private Color moveHighlightColor = new Color(0.2f, 0.8f, 0.2f, 0.5f);
        [SerializeField] private Color attackHighlightColor = new Color(0.8f, 0.2f, 0.2f, 0.5f);
        [SerializeField] private Color selectedColor = new Color(1f, 0.9f, 0f, 0.5f);
        [SerializeField] private Color player1Color = new Color(0.2f, 0.4f, 0.8f);
        [SerializeField] private Color player2Color = new Color(0.8f, 0.2f, 0.2f);

        // Ссылки на созданные объекты
        private Dictionary<Vector2Int, CellController> _cells = new Dictionary<Vector2Int, CellController>();
        private Dictionary<int, UnitController> _units = new Dictionary<int, UnitController>();
        private List<GameObject> _obstacles = new List<GameObject>();

        private int _fieldWidth;
        private int _fieldHeight;

        private void Start()
        {
            // Подписаться на события GameManager
            if (GameManager.Instance != null)
            {
                GameManager.Instance.OnGameStateUpdated += OnGameStateUpdated;
                GameManager.Instance.OnUnitActionsReceived += OnUnitActionsReceived;
                GameManager.Instance.OnMoveCompleted += OnMoveCompleted;

                // Если игра уже загружена, обновить поле
                if (GameManager.Instance.CurrentState.GameId > 0)
                {
                    OnGameStateUpdated(GameManager.Instance.CurrentState);
                }
            }
        }

        private void OnDestroy()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.OnGameStateUpdated -= OnGameStateUpdated;
                GameManager.Instance.OnUnitActionsReceived -= OnUnitActionsReceived;
                GameManager.Instance.OnMoveCompleted -= OnMoveCompleted;
            }
        }

        #region Board Creation

        /// <summary>
        /// Создать игровое поле
        /// </summary>
        public void CreateBoard(int width, int height)
        {
            ClearBoard();
            _fieldWidth = width;
            _fieldHeight = height;

            // Центрировать доску
            Vector3 offset = new Vector3(
                -(width - 1) * cellSize / 2f,
                -(height - 1) * cellSize / 2f,
                0
            );

            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    Vector3 position = new Vector3(x * cellSize, y * cellSize, 0) + offset;
                    GameObject cellObj = Instantiate(cellPrefab, position, Quaternion.identity, transform);
                    cellObj.name = $"Cell_{GetCoordinateName(x, y)}";

                    CellController cell = cellObj.GetComponent<CellController>();
                    if (cell != null)
                    {
                        // Шахматная раскраска
                        bool isLight = (x + y) % 2 == 0;
                        cell.Initialize(x, y, isLight ? lightCellColor : darkCellColor);
                        cell.OnCellClicked += HandleCellClick;

                        _cells[new Vector2Int(x, y)] = cell;
                    }
                }
            }

            // Добавить координаты (по желанию - можно включить через UI)
            // CreateCoordinateLabels(width, height, offset);
        }

        /// <summary>
        /// Очистить доску
        /// </summary>
        public void ClearBoard()
        {
            foreach (var cell in _cells.Values)
            {
                if (cell != null)
                {
                    cell.OnCellClicked -= HandleCellClick;
                    Destroy(cell.gameObject);
                }
            }
            _cells.Clear();

            foreach (var unit in _units.Values)
            {
                if (unit != null)
                {
                    Destroy(unit.gameObject);
                }
            }
            _units.Clear();

            foreach (var obstacle in _obstacles)
            {
                if (obstacle != null)
                {
                    Destroy(obstacle);
                }
            }
            _obstacles.Clear();
        }

        /// <summary>
        /// Разместить препятствия
        /// </summary>
        public void PlaceObstacles(List<ObstacleInfo> obstacles)
        {
            foreach (var obs in obstacles)
            {
                if (_cells.TryGetValue(new Vector2Int(obs.x, obs.y), out CellController cell))
                {
                    GameObject obsObj = Instantiate(obstaclePrefab, cell.transform.position, Quaternion.identity, transform);
                    obsObj.name = $"Obstacle_{obs.x}_{obs.y}";
                    _obstacles.Add(obsObj);
                }
            }
        }

        /// <summary>
        /// Разместить юнитов
        /// </summary>
        public void PlaceUnits(List<UnitInfo> units)
        {
            // Удалить старых юнитов
            foreach (var unit in _units.Values)
            {
                if (unit != null) Destroy(unit.gameObject);
            }
            _units.Clear();

            // Создать новых
            foreach (var unitInfo in units)
            {
                CreateUnit(unitInfo);
            }
        }

        /// <summary>
        /// Создать юнита на поле
        /// </summary>
        private UnitController CreateUnit(UnitInfo unitInfo)
        {
            if (!_cells.TryGetValue(new Vector2Int(unitInfo.x, unitInfo.y), out CellController cell))
            {
                Debug.LogError($"Cell not found at {unitInfo.x},{unitInfo.y}");
                return null;
            }

            GameObject unitObj = Instantiate(unitPrefab, cell.transform.position, Quaternion.identity, transform);
            unitObj.name = $"Unit_{unitInfo.unit_type.name}_{unitInfo.id}";

            UnitController unit = unitObj.GetComponent<UnitController>();
            if (unit != null)
            {
                bool isPlayer1 = unitInfo.player_id == GameManager.Instance.CurrentState.Player1Id;
                Color playerColor = isPlayer1 ? player1Color : player2Color;

                unit.Initialize(unitInfo, playerColor);
                unit.OnUnitClicked += HandleUnitClick;

                _units[unitInfo.id] = unit;
            }

            return unit;
        }

        #endregion

        #region Highlighting

        /// <summary>
        /// Подсветить возможные ходы
        /// </summary>
        public void HighlightMoves(List<MoveTarget> moves)
        {
            foreach (var move in moves)
            {
                if (_cells.TryGetValue(new Vector2Int(move.x, move.y), out CellController cell))
                {
                    cell.SetHighlight(moveHighlightColor, CellHighlightType.Move);
                }
            }
        }

        /// <summary>
        /// Подсветить возможные атаки
        /// </summary>
        public void HighlightAttacks(List<AttackTarget> attacks)
        {
            foreach (var attack in attacks)
            {
                if (_cells.TryGetValue(new Vector2Int(attack.x, attack.y), out CellController cell))
                {
                    cell.SetHighlight(attackHighlightColor, CellHighlightType.Attack);
                }
            }
        }

        /// <summary>
        /// Подсветить выбранную клетку
        /// </summary>
        public void HighlightSelected(int x, int y)
        {
            if (_cells.TryGetValue(new Vector2Int(x, y), out CellController cell))
            {
                cell.SetHighlight(selectedColor, CellHighlightType.Selected);
            }
        }

        /// <summary>
        /// Убрать всю подсветку
        /// </summary>
        public void ClearAllHighlights()
        {
            foreach (var cell in _cells.Values)
            {
                cell.ClearHighlight();
            }
        }

        #endregion

        #region Event Handlers

        private void OnGameStateUpdated(ClientGameState state)
        {
            // Создать доску если нужно
            if (_fieldWidth != state.FieldWidth || _fieldHeight != state.FieldHeight)
            {
                CreateBoard(state.FieldWidth, state.FieldHeight);
                PlaceObstacles(state.Obstacles);
            }

            // Обновить юнитов
            UpdateUnits(state.Units);
        }

        private void OnUnitActionsReceived(UnitActionsResponse actions)
        {
            ClearAllHighlights();

            if (GameManager.Instance.SelectedUnit != null)
            {
                var unit = GameManager.Instance.SelectedUnit;
                HighlightSelected(unit.x, unit.y);
                HighlightMoves(actions.can_move);
                HighlightAttacks(actions.can_attack);
            }
        }

        private void OnMoveCompleted(MoveResponse response)
        {
            ClearAllHighlights();
        }

        private void HandleCellClick(int x, int y)
        {
            Debug.Log($"Cell clicked: {x}, {y}");

            if (GameManager.Instance.SelectedUnit != null)
            {
                if (GameManager.Instance.CanMoveTo(x, y))
                {
                    GameManager.Instance.MoveSelectedUnit(x, y);
                }
                else
                {
                    // Клик на пустую клетку - отменить выбор
                    GameManager.Instance.DeselectUnit();
                    ClearAllHighlights();
                }
            }
        }

        private void HandleUnitClick(int unitId)
        {
            Debug.Log($"Unit clicked: {unitId}");

            UnitInfo clickedUnit = GameManager.Instance.GetUnitById(unitId);
            if (clickedUnit == null) return;

            // Если это вражеский юнит и можно атаковать
            if (GameManager.Instance.SelectedUnit != null &&
                clickedUnit.player_id != GameManager.Instance.CurrentPlayerId &&
                GameManager.Instance.CanAttack(unitId))
            {
                GameManager.Instance.AttackWithSelectedUnit(unitId);
                return;
            }

            // Если это свой юнит - выбрать его
            if (clickedUnit.player_id == GameManager.Instance.CurrentPlayerId)
            {
                ClearAllHighlights();
                GameManager.Instance.SelectUnit(clickedUnit);
            }
        }

        #endregion

        #region Helpers

        private void UpdateUnits(List<UnitInfo> units)
        {
            // Отметить существующих юнитов как не обновлённые
            HashSet<int> existingIds = new HashSet<int>(_units.Keys);

            foreach (var unitInfo in units)
            {
                existingIds.Remove(unitInfo.id);

                if (_units.TryGetValue(unitInfo.id, out UnitController unit))
                {
                    // Обновить существующего юнита
                    unit.UpdateInfo(unitInfo);

                    // Переместить если позиция изменилась
                    if (_cells.TryGetValue(new Vector2Int(unitInfo.x, unitInfo.y), out CellController cell))
                    {
                        unit.MoveTo(cell.transform.position);
                    }
                }
                else
                {
                    // Создать нового юнита
                    CreateUnit(unitInfo);
                }
            }

            // Удалить юнитов которых больше нет
            foreach (int id in existingIds)
            {
                if (_units.TryGetValue(id, out UnitController unit))
                {
                    unit.OnUnitClicked -= HandleUnitClick;
                    Destroy(unit.gameObject);
                    _units.Remove(id);
                }
            }
        }

        private string GetCoordinateName(int x, int y)
        {
            char col = (char)('A' + x);
            int row = y + 1;
            return $"{col}{row}";
        }

        #endregion
    }

    public enum CellHighlightType
    {
        None,
        Move,
        Attack,
        Selected
    }
}
