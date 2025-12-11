using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;

namespace ModernHomm.UI
{
    /// <summary>
    /// Панель информации об игроке и его юнитах
    /// </summary>
    public class UnitInfoPanel : MonoBehaviour
    {
        [Header("Player Info")]
        [SerializeField] private TextMeshProUGUI playerNameText;
        [SerializeField] private Image playerColorIndicator;

        [Header("Unit Portrait")]
        [SerializeField] private GameObject portraitPanel;
        [SerializeField] private Image unitImage;
        [SerializeField] private TextMeshProUGUI unitNameText;
        [SerializeField] private TextMeshProUGUI unitIconText;
        [SerializeField] private TextMeshProUGUI unitDamageText;
        [SerializeField] private TextMeshProUGUI unitDefenseText;
        [SerializeField] private TextMeshProUGUI unitHealthText;
        [SerializeField] private TextMeshProUGUI unitCountText;

        [Header("Unit List")]
        [SerializeField] private Transform unitListContainer;
        [SerializeField] private GameObject unitListItemPrefab;

        [Header("Colors")]
        [SerializeField] private Color friendlyColor = new Color(0.2f, 0.4f, 0.8f);
        [SerializeField] private Color enemyColor = new Color(0.8f, 0.2f, 0.2f);

        private int _playerId;
        private bool _isFriendly;
        private List<GameObject> _listItems = new List<GameObject>();

        public void SetPlayer(string name, int playerId, List<UnitInfo> allUnits, bool isFriendly)
        {
            _playerId = playerId;
            _isFriendly = isFriendly;

            // Имя игрока
            if (playerNameText != null)
            {
                playerNameText.text = name;
            }

            // Цвет
            if (playerColorIndicator != null)
            {
                playerColorIndicator.color = isFriendly ? friendlyColor : enemyColor;
            }

            // Список юнитов этого игрока
            var playerUnits = allUnits.Where(u => u.player_id == playerId).ToList();
            UpdateUnitList(playerUnits);

            // Скрыть портрет по умолчанию
            HidePortrait();
        }

        public void ShowUnitPortrait(UnitInfo unit)
        {
            if (unit == null || unit.unit_type == null)
            {
                HidePortrait();
                return;
            }

            if (portraitPanel != null)
            {
                portraitPanel.SetActive(true);
            }

            // Иконка
            if (unitIconText != null)
            {
                unitIconText.text = unit.unit_type.icon ?? "🎮";
            }

            // Имя
            if (unitNameText != null)
            {
                unitNameText.text = unit.unit_type.name;
            }

            // Статистика
            if (unitDamageText != null)
            {
                unitDamageText.text = $"⚔️ {unit.unit_type.damage}";
            }

            if (unitDefenseText != null)
            {
                unitDefenseText.text = $"🛡️ {unit.unit_type.defense}";
            }

            if (unitHealthText != null)
            {
                unitHealthText.text = $"❤️ {unit.hp}/{unit.unit_type.health}";
            }

            if (unitCountText != null)
            {
                unitCountText.text = $"📍 x{unit.count}";
            }

            // Картинка (если есть)
            // TODO: Загрузить изображение из unit.unit_type.image_path
        }

        public void HidePortrait()
        {
            if (portraitPanel != null)
            {
                portraitPanel.SetActive(false);
            }
        }

        private void UpdateUnitList(List<UnitInfo> units)
        {
            // Очистить старые элементы
            foreach (var item in _listItems)
            {
                if (item != null) Destroy(item);
            }
            _listItems.Clear();

            if (unitListContainer == null || unitListItemPrefab == null) return;

            // Создать новые элементы
            foreach (var unit in units.OrderBy(u => u.unit_type?.name))
            {
                GameObject item = Instantiate(unitListItemPrefab, unitListContainer);
                _listItems.Add(item);

                // Найти компоненты в префабе
                TextMeshProUGUI nameText = item.GetComponentInChildren<TextMeshProUGUI>();
                if (nameText != null)
                {
                    string icon = unit.unit_type?.icon ?? "🎮";
                    string name = unit.unit_type?.name ?? "???";
                    string readyIcon = unit.has_moved ? "⬜" : "🟢";
                    nameText.text = $"{readyIcon} {icon} {name} x{unit.count}";
                }

                // Добавить обработчик клика
                Button button = item.GetComponent<Button>();
                if (button != null)
                {
                    int unitId = unit.id;
                    button.onClick.AddListener(() => OnUnitListItemClicked(unitId));
                }
            }
        }

        private void OnUnitListItemClicked(int unitId)
        {
            UnitInfo unit = GameManager.Instance.GetUnitById(unitId);
            if (unit == null) return;

            // Показать портрет
            ShowUnitPortrait(unit);

            // Если свой юнит - выбрать его
            if (_isFriendly && unit.player_id == GameManager.Instance.CurrentPlayerId)
            {
                GameManager.Instance.SelectUnit(unit);
            }
        }
    }
}
