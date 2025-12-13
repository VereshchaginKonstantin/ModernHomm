using UnityEngine;
using UnityEditor;
using TMPro;

namespace ModernHomm.Editor
{
    /// <summary>
    /// Автоматическая привязка SerializedField ссылок в префабах
    /// Запускается после создания сцен
    /// </summary>
    public class PrefabLinker : EditorWindow
    {
        [MenuItem("ModernHomm/Link Prefab References", false, 20)]
        public static void LinkAllReferences()
        {
            LinkCellPrefab();
            LinkUnitPrefab();
            LinkSceneReferences();

            AssetDatabase.SaveAssets();
            Debug.Log("[ModernHomm] Все ссылки привязаны!");
        }

        private static void LinkCellPrefab()
        {
            string path = "Assets/Prefabs/Cell.prefab";
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) return;

            var controller = prefab.GetComponent<ModernHomm.Board.CellController>();
            if (controller == null) return;

            SerializedObject so = new SerializedObject(controller);

            // Найти children
            Transform bg = prefab.transform.Find("Background");
            Transform highlight = prefab.transform.Find("Highlight");
            BoxCollider2D collider = prefab.GetComponent<BoxCollider2D>();

            if (bg != null)
            {
                var bgRenderer = bg.GetComponent<SpriteRenderer>();
                so.FindProperty("backgroundRenderer").objectReferenceValue = bgRenderer;
            }

            if (highlight != null)
            {
                var hlRenderer = highlight.GetComponent<SpriteRenderer>();
                so.FindProperty("highlightRenderer").objectReferenceValue = hlRenderer;
            }

            if (collider != null)
            {
                so.FindProperty("clickCollider").objectReferenceValue = collider;
            }

            so.ApplyModifiedProperties();
            EditorUtility.SetDirty(prefab);
            Debug.Log("[ModernHomm] Cell prefab linked");
        }

        private static void LinkUnitPrefab()
        {
            string path = "Assets/Prefabs/Unit.prefab";
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) return;

            var controller = prefab.GetComponent<ModernHomm.Board.UnitController>();
            if (controller == null) return;

            SerializedObject so = new SerializedObject(controller);

            // Найти children
            Transform bg = prefab.transform.Find("Background");
            Transform icon = prefab.transform.Find("Icon");
            Transform countObj = prefab.transform.Find("CountText");
            Transform ready = prefab.transform.Find("ReadyIndicator");
            Transform selection = prefab.transform.Find("SelectionIndicator");

            if (bg != null)
            {
                so.FindProperty("backgroundRenderer").objectReferenceValue = bg.GetComponent<SpriteRenderer>();
            }

            if (icon != null)
            {
                so.FindProperty("iconRenderer").objectReferenceValue = icon.GetComponent<SpriteRenderer>();
            }

            if (countObj != null)
            {
                so.FindProperty("countText").objectReferenceValue = countObj.GetComponent<TextMeshPro>();
            }

            if (ready != null)
            {
                so.FindProperty("readyIndicator").objectReferenceValue = ready.gameObject;
            }

            if (selection != null)
            {
                so.FindProperty("selectionIndicator").objectReferenceValue = selection.GetComponent<SpriteRenderer>();
            }

            so.ApplyModifiedProperties();
            EditorUtility.SetDirty(prefab);
            Debug.Log("[ModernHomm] Unit prefab linked");
        }

        private static void LinkSceneReferences()
        {
            // Эти ссылки лучше настраивать вручную после открытия сцены
            // Поскольку объекты сцены не доступны из Editor скрипта без открытия сцены
            Debug.Log("[ModernHomm] Ссылки на сцене нужно настроить вручную через меню ModernHomm → Link Scene References In Open Scene");
        }

        [MenuItem("ModernHomm/Link Scene References (Current Scene)", false, 21)]
        public static void LinkCurrentSceneReferences()
        {
            // Board Controller
            var boardController = Object.FindObjectOfType<ModernHomm.Board.BoardController>();
            if (boardController != null)
            {
                SerializedObject so = new SerializedObject(boardController);

                GameObject cellPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Cell.prefab");
                GameObject unitPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Unit.prefab");
                GameObject obstaclePrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Obstacle.prefab");

                if (cellPrefab != null)
                    so.FindProperty("cellPrefab").objectReferenceValue = cellPrefab;
                if (unitPrefab != null)
                    so.FindProperty("unitPrefab").objectReferenceValue = unitPrefab;
                if (obstaclePrefab != null)
                    so.FindProperty("obstaclePrefab").objectReferenceValue = obstaclePrefab;

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(boardController);
                Debug.Log("[ModernHomm] BoardController linked");
            }

            // GameLogUI
            var gameLogUI = Object.FindObjectOfType<ModernHomm.UI.GameLogUI>();
            if (gameLogUI != null)
            {
                SerializedObject so = new SerializedObject(gameLogUI);

                GameObject logEntryPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/UI/LogEntry.prefab");
                if (logEntryPrefab != null)
                    so.FindProperty("logEntryPrefab").objectReferenceValue = logEntryPrefab;

                // Найти контейнер
                var scrollView = gameLogUI.transform.Find("LogScrollView");
                if (scrollView != null)
                {
                    var content = scrollView.Find("Viewport/Content");
                    if (content != null)
                    {
                        so.FindProperty("logContainer").objectReferenceValue = content;
                    }

                    var scrollRect = scrollView.GetComponent<UnityEngine.UI.ScrollRect>();
                    if (scrollRect != null)
                    {
                        so.FindProperty("scrollRect").objectReferenceValue = scrollRect;
                    }
                }

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(gameLogUI);
                Debug.Log("[ModernHomm] GameLogUI linked");
            }

            // UnitInfoPanel
            var unitInfoPanels = Object.FindObjectsOfType<ModernHomm.UI.UnitInfoPanel>();
            foreach (var panel in unitInfoPanels)
            {
                SerializedObject so = new SerializedObject(panel);

                GameObject unitListItemPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/UI/UnitListItem.prefab");
                if (unitListItemPrefab != null)
                    so.FindProperty("unitListItemPrefab").objectReferenceValue = unitListItemPrefab;

                // Автопоиск компонентов в children
                LinkChildComponent<TextMeshProUGUI>(so, panel.transform, "PlayerNameText", "playerNameText");
                LinkChildComponent<UnityEngine.UI.Image>(so, panel.transform, "PlayerColorIndicator", "playerColorIndicator");

                var portrait = panel.transform.Find("PortraitPanel");
                if (portrait != null)
                {
                    so.FindProperty("portraitPanel").objectReferenceValue = portrait.gameObject;
                    LinkChildComponent<TextMeshProUGUI>(so, portrait, "UnitIconText", "unitIconText");
                    LinkChildComponent<TextMeshProUGUI>(so, portrait, "UnitNameText", "unitNameText");
                    LinkChildComponent<TextMeshProUGUI>(so, portrait, "UnitDamageText", "unitDamageText");
                    LinkChildComponent<TextMeshProUGUI>(so, portrait, "UnitDefenseText", "unitDefenseText");
                    LinkChildComponent<TextMeshProUGUI>(so, portrait, "UnitHealthText", "unitHealthText");
                    LinkChildComponent<TextMeshProUGUI>(so, portrait, "UnitCountText", "unitCountText");
                }

                var unitListScroll = panel.transform.Find("UnitListScroll");
                if (unitListScroll != null)
                {
                    var content = unitListScroll.Find("Viewport/Content");
                    if (content != null)
                    {
                        so.FindProperty("unitListContainer").objectReferenceValue = content;
                    }
                }

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(panel);
            }
            Debug.Log($"[ModernHomm] {unitInfoPanels.Length} UnitInfoPanel(s) linked");

            // PlayerSelectUI (MainMenu)
            var playerSelectUI = Object.FindObjectOfType<ModernHomm.UI.PlayerSelectUI>();
            if (playerSelectUI != null)
            {
                SerializedObject so = new SerializedObject(playerSelectUI);

                LinkChildComponentRecursive<TextMeshProUGUI>(so, playerSelectUI.transform, "PlayerNameText", "playerNameText");
                LinkChildComponentRecursive<TextMeshProUGUI>(so, playerSelectUI.transform, "BalanceText", "playerBalanceText");
                LinkChildComponentRecursive<TextMeshProUGUI>(so, playerSelectUI.transform, "ArmyCostText", "playerArmyCostText");
                LinkChildComponentRecursive<TextMeshProUGUI>(so, playerSelectUI.transform, "StatsText", "playerStatsText");
                LinkChildComponentRecursive<TMP_Dropdown>(so, playerSelectUI.transform, "OpponentDropdown", "opponentDropdown");
                LinkChildComponentRecursive<TextMeshProUGUI>(so, playerSelectUI.transform, "OpponentInfoText", "opponentInfoText");
                LinkChildComponentRecursive<TMP_Dropdown>(so, playerSelectUI.transform, "FieldSizeDropdown", "fieldSizeDropdown");
                LinkChildComponentRecursive<UnityEngine.UI.Button>(so, playerSelectUI.transform, "StartBattleButton", "startBattleButton");
                LinkChildComponentRecursive<TextMeshProUGUI>(so, playerSelectUI.transform, "StatusText", "statusText");

                // Pending panel
                var pendingPanel = FindChildRecursive(playerSelectUI.transform, "PendingGamePanel");
                if (pendingPanel != null)
                {
                    so.FindProperty("pendingGamePanel").objectReferenceValue = pendingPanel.gameObject;
                    LinkChildComponent<TextMeshProUGUI>(so, pendingPanel, "PendingGameText", "pendingGameText");
                    LinkChildComponent<UnityEngine.UI.Button>(so, pendingPanel, "AcceptButton", "acceptButton");
                    LinkChildComponent<UnityEngine.UI.Button>(so, pendingPanel, "DeclineButton", "declineButton");
                }

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(playerSelectUI);
                Debug.Log("[ModernHomm] PlayerSelectUI linked");
            }

            // GameBoardUI
            var gameBoardUI = Object.FindObjectOfType<ModernHomm.UI.GameBoardUI>();
            if (gameBoardUI != null)
            {
                SerializedObject so = new SerializedObject(gameBoardUI);

                // Панели игроков
                var player1Panel = Object.FindObjectOfType<ModernHomm.UI.UnitInfoPanel>();
                var allPanels = Object.FindObjectsOfType<ModernHomm.UI.UnitInfoPanel>();
                if (allPanels.Length >= 2)
                {
                    so.FindProperty("player1Panel").objectReferenceValue = allPanels[0];
                    so.FindProperty("player2Panel").objectReferenceValue = allPanels[1];
                }

                // Turn indicator
                LinkChildComponentRecursive<TextMeshProUGUI>(so, gameBoardUI.transform.root, "TurnIndicatorText", "turnIndicatorText");
                var topPanel = FindChildRecursive(gameBoardUI.transform.root, "TopPanel");
                if (topPanel != null)
                {
                    so.FindProperty("turnIndicatorBackground").objectReferenceValue = topPanel.GetComponent<UnityEngine.UI.Image>();
                }

                // Action panel
                var actionPanel = Object.FindObjectOfType<ModernHomm.UI.ActionPanel>();
                if (actionPanel != null)
                {
                    so.FindProperty("actionPanel").objectReferenceValue = actionPanel;
                }

                // Game log
                var gameLog = Object.FindObjectOfType<ModernHomm.UI.GameLogUI>();
                if (gameLog != null)
                {
                    so.FindProperty("gameLogUI").objectReferenceValue = gameLog;
                }

                // Overlay
                var overlay = Object.FindObjectOfType<ModernHomm.UI.OverlayUI>();
                if (overlay != null)
                {
                    so.FindProperty("overlayUI").objectReferenceValue = overlay;
                }

                // Hint
                LinkChildComponentRecursive<TextMeshProUGUI>(so, gameBoardUI.transform.root, "HintText", "hintText");

                // Board
                if (boardController != null)
                {
                    so.FindProperty("boardController").objectReferenceValue = boardController;
                }

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(gameBoardUI);
                Debug.Log("[ModernHomm] GameBoardUI linked");
            }

            // ActionPanel
            var actionPanelComp = Object.FindObjectOfType<ModernHomm.UI.ActionPanel>();
            if (actionPanelComp != null)
            {
                SerializedObject so = new SerializedObject(actionPanelComp);

                LinkChildComponent<UnityEngine.UI.Button>(so, actionPanelComp.transform, "MoveButton", "moveButton");
                LinkChildComponent<UnityEngine.UI.Button>(so, actionPanelComp.transform, "AttackButton", "attackButton");
                LinkChildComponent<UnityEngine.UI.Button>(so, actionPanelComp.transform, "SkipButton", "skipButton");
                LinkChildComponent<UnityEngine.UI.Button>(so, actionPanelComp.transform, "DeferButton", "deferButton");
                LinkChildComponent<UnityEngine.UI.Button>(so, actionPanelComp.transform, "SurrenderButton", "surrenderButton");

                var canvasGroup = actionPanelComp.GetComponent<CanvasGroup>();
                if (canvasGroup == null)
                {
                    canvasGroup = actionPanelComp.gameObject.AddComponent<CanvasGroup>();
                }
                so.FindProperty("canvasGroup").objectReferenceValue = canvasGroup;

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(actionPanelComp);
                Debug.Log("[ModernHomm] ActionPanel linked");
            }

            // OverlayUI
            var overlayUI = Object.FindObjectOfType<ModernHomm.UI.OverlayUI>();
            if (overlayUI != null)
            {
                SerializedObject so = new SerializedObject(overlayUI);

                var battleResult = FindChildRecursive(overlayUI.transform, "BattleResultPanel");
                if (battleResult != null)
                {
                    so.FindProperty("battleResultPanel").objectReferenceValue = battleResult.gameObject;
                    LinkChildComponent<TextMeshProUGUI>(so, battleResult, "BattleResultText", "battleResultText");
                }

                var gameOver = FindChildRecursive(overlayUI.transform, "GameOverPanel");
                if (gameOver != null)
                {
                    so.FindProperty("gameOverPanel").objectReferenceValue = gameOver.gameObject;
                    LinkChildComponent<TextMeshProUGUI>(so, gameOver, "GameOverTitle", "gameOverTitle");
                    LinkChildComponent<TextMeshProUGUI>(so, gameOver, "GameOverSubtitle", "gameOverSubtitle");
                    LinkChildComponent<TextMeshProUGUI>(so, gameOver, "GameOverStats", "gameOverStats");
                    LinkChildComponent<UnityEngine.UI.Button>(so, gameOver, "ReturnButton", "returnButton");
                }

                so.ApplyModifiedProperties();
                EditorUtility.SetDirty(overlayUI);
                Debug.Log("[ModernHomm] OverlayUI linked");
            }

            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(
                UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene());

            Debug.Log("[ModernHomm] Все ссылки в текущей сцене привязаны!");
        }

        private static void LinkChildComponent<T>(SerializedObject so, Transform parent, string childName, string propertyName) where T : Component
        {
            var child = parent.Find(childName);
            if (child != null)
            {
                var component = child.GetComponent<T>();
                if (component != null)
                {
                    var prop = so.FindProperty(propertyName);
                    if (prop != null)
                    {
                        prop.objectReferenceValue = component;
                    }
                }
            }
        }

        private static void LinkChildComponentRecursive<T>(SerializedObject so, Transform root, string childName, string propertyName) where T : Component
        {
            var child = FindChildRecursive(root, childName);
            if (child != null)
            {
                var component = child.GetComponent<T>();
                if (component != null)
                {
                    var prop = so.FindProperty(propertyName);
                    if (prop != null)
                    {
                        prop.objectReferenceValue = component;
                    }
                }
            }
        }

        private static Transform FindChildRecursive(Transform parent, string name)
        {
            if (parent.name == name) return parent;

            foreach (Transform child in parent)
            {
                var found = FindChildRecursive(child, name);
                if (found != null) return found;
            }

            return null;
        }
    }
}
