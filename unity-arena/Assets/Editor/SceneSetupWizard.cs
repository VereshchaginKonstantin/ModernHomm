using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using TMPro;
using System.IO;

namespace ModernHomm.Editor
{
    /// <summary>
    /// Мастер автоматической настройки сцен и префабов для Unity Arena
    /// Меню: ModernHomm → Setup All
    /// </summary>
    public class SceneSetupWizard : EditorWindow
    {
        private static string ScenesPath = "Assets/Scenes";
        private static string PrefabsPath = "Assets/Prefabs";
        private static string MaterialsPath = "Assets/Materials";

        [MenuItem("ModernHomm/Setup All (Scenes + Prefabs)", false, 0)]
        public static void SetupAll()
        {
            if (!EditorUtility.DisplayDialog("Setup ModernHomm Arena",
                "Это создаст:\n" +
                "- 3 сцены (Bootstrap, MainMenu, Battle)\n" +
                "- Префабы (Cell, Unit, Obstacle, UI элементы)\n" +
                "- Материалы\n\n" +
                "Продолжить?", "Да", "Отмена"))
            {
                return;
            }

            CreateFolders();
            CreateMaterials();
            CreatePrefabs();
            CreateBootstrapScene();
            CreateMainMenuScene();
            CreateBattleScene();
            SetupBuildSettings();

            EditorUtility.DisplayDialog("Готово!",
                "Все сцены и префабы созданы.\n\n" +
                "Откройте сцену Bootstrap и нажмите Play для тестирования.\n\n" +
                "Не забудьте импортировать TMP Essentials:\n" +
                "Window → TextMeshPro → Import TMP Essential Resources",
                "OK");
        }

        [MenuItem("ModernHomm/Create Scenes Only", false, 10)]
        public static void CreateScenesOnly()
        {
            CreateFolders();
            CreateBootstrapScene();
            CreateMainMenuScene();
            CreateBattleScene();
            SetupBuildSettings();
            Debug.Log("[ModernHomm] Сцены созданы!");
        }

        [MenuItem("ModernHomm/Create Prefabs Only", false, 11)]
        public static void CreatePrefabsOnly()
        {
            CreateFolders();
            CreateMaterials();
            CreatePrefabs();
            Debug.Log("[ModernHomm] Префабы созданы!");
        }

        #region Folders

        private static void CreateFolders()
        {
            CreateFolderIfNotExists("Assets/Scenes");
            CreateFolderIfNotExists("Assets/Prefabs");
            CreateFolderIfNotExists("Assets/Prefabs/UI");
            CreateFolderIfNotExists("Assets/Materials");
            AssetDatabase.Refresh();
        }

        private static void CreateFolderIfNotExists(string path)
        {
            if (!AssetDatabase.IsValidFolder(path))
            {
                string parent = Path.GetDirectoryName(path);
                string folderName = Path.GetFileName(path);
                AssetDatabase.CreateFolder(parent, folderName);
            }
        }

        #endregion

        #region Materials

        private static Material _whiteMaterial;
        private static Material _cellLightMaterial;
        private static Material _cellDarkMaterial;
        private static Material _highlightMaterial;
        private static Material _player1Material;
        private static Material _player2Material;

        private static void CreateMaterials()
        {
            // Используем стандартный спрайтовый шейдер
            Shader spriteShader = Shader.Find("Sprites/Default");
            if (spriteShader == null)
            {
                spriteShader = Shader.Find("UI/Default");
            }

            _whiteMaterial = CreateMaterial("WhiteMaterial", Color.white, spriteShader);
            _cellLightMaterial = CreateMaterial("CellLightMaterial", new Color(0.9f, 0.9f, 0.85f), spriteShader);
            _cellDarkMaterial = CreateMaterial("CellDarkMaterial", new Color(0.6f, 0.6f, 0.55f), spriteShader);
            _highlightMaterial = CreateMaterial("HighlightMaterial", new Color(0.2f, 0.8f, 0.2f, 0.5f), spriteShader);
            _player1Material = CreateMaterial("Player1Material", new Color(0.2f, 0.4f, 0.8f, 0.8f), spriteShader);
            _player2Material = CreateMaterial("Player2Material", new Color(0.8f, 0.2f, 0.2f, 0.8f), spriteShader);

            AssetDatabase.SaveAssets();
        }

        private static Material CreateMaterial(string name, Color color, Shader shader)
        {
            string path = $"{MaterialsPath}/{name}.mat";
            Material mat = AssetDatabase.LoadAssetAtPath<Material>(path);

            if (mat == null)
            {
                mat = new Material(shader);
                mat.color = color;
                AssetDatabase.CreateAsset(mat, path);
            }

            return mat;
        }

        #endregion

        #region Prefabs

        private static GameObject _cellPrefab;
        private static GameObject _unitPrefab;
        private static GameObject _obstaclePrefab;
        private static GameObject _logEntryPrefab;
        private static GameObject _unitListItemPrefab;

        private static void CreatePrefabs()
        {
            _cellPrefab = CreateCellPrefab();
            _unitPrefab = CreateUnitPrefab();
            _obstaclePrefab = CreateObstaclePrefab();
            _logEntryPrefab = CreateLogEntryPrefab();
            _unitListItemPrefab = CreateUnitListItemPrefab();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        private static GameObject CreateCellPrefab()
        {
            string path = $"{PrefabsPath}/Cell.prefab";
            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing != null) return existing;

            GameObject cell = new GameObject("Cell");

            // Background
            GameObject bg = new GameObject("Background");
            bg.transform.SetParent(cell.transform);
            var bgRenderer = bg.AddComponent<SpriteRenderer>();
            bgRenderer.sprite = CreateSquareSprite();
            bgRenderer.sortingOrder = 0;

            // Highlight
            GameObject highlight = new GameObject("Highlight");
            highlight.transform.SetParent(cell.transform);
            var hlRenderer = highlight.AddComponent<SpriteRenderer>();
            hlRenderer.sprite = CreateSquareSprite();
            hlRenderer.sortingOrder = 1;
            hlRenderer.enabled = false;

            // Collider
            var collider = cell.AddComponent<BoxCollider2D>();
            collider.size = Vector2.one;

            // Script
            var controller = cell.AddComponent<ModernHomm.Board.CellController>();

            // Сериализуем ссылки через SerializedObject
            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(cell, path);
            Object.DestroyImmediate(cell);

            return prefab;
        }

        private static GameObject CreateUnitPrefab()
        {
            string path = $"{PrefabsPath}/Unit.prefab";
            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing != null) return existing;

            GameObject unit = new GameObject("Unit");

            // Background
            GameObject bg = new GameObject("Background");
            bg.transform.SetParent(unit.transform);
            bg.transform.localScale = Vector3.one * 0.9f;
            var bgRenderer = bg.AddComponent<SpriteRenderer>();
            bgRenderer.sprite = CreateCircleSprite();
            bgRenderer.sortingOrder = 2;
            bgRenderer.color = new Color(0.3f, 0.5f, 0.8f, 0.8f);

            // Icon (TextMeshPro для emoji)
            GameObject icon = new GameObject("Icon");
            icon.transform.SetParent(unit.transform);
            icon.transform.localPosition = new Vector3(0, 0.1f, 0);
            var iconText = icon.AddComponent<TextMeshPro>();
            iconText.text = "⚔️";
            iconText.fontSize = 3;
            iconText.alignment = TextAlignmentOptions.Center;
            iconText.sortingOrder = 3;

            // Count text
            GameObject countObj = new GameObject("CountText");
            countObj.transform.SetParent(unit.transform);
            countObj.transform.localPosition = new Vector3(0.3f, -0.3f, 0);
            var countText = countObj.AddComponent<TextMeshPro>();
            countText.text = "x5";
            countText.fontSize = 2;
            countText.alignment = TextAlignmentOptions.Center;
            countText.sortingOrder = 4;
            countText.color = Color.white;

            // Ready indicator
            GameObject ready = new GameObject("ReadyIndicator");
            ready.transform.SetParent(unit.transform);
            ready.transform.localPosition = new Vector3(-0.35f, 0.35f, 0);
            ready.transform.localScale = Vector3.one * 0.2f;
            var readyRenderer = ready.AddComponent<SpriteRenderer>();
            readyRenderer.sprite = CreateCircleSprite();
            readyRenderer.color = Color.green;
            readyRenderer.sortingOrder = 5;

            // Selection indicator
            GameObject selection = new GameObject("SelectionIndicator");
            selection.transform.SetParent(unit.transform);
            selection.transform.localScale = Vector3.one * 1.1f;
            var selRenderer = selection.AddComponent<SpriteRenderer>();
            selRenderer.sprite = CreateRingSprite();
            selRenderer.color = new Color(1f, 0.9f, 0f, 0.8f);
            selRenderer.sortingOrder = 1;
            selRenderer.enabled = false;

            // Collider
            var collider = unit.AddComponent<BoxCollider2D>();
            collider.size = Vector2.one * 0.9f;

            // Script
            unit.AddComponent<ModernHomm.Board.UnitController>();

            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(unit, path);
            Object.DestroyImmediate(unit);

            return prefab;
        }

        private static GameObject CreateObstaclePrefab()
        {
            string path = $"{PrefabsPath}/Obstacle.prefab";
            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing != null) return existing;

            GameObject obstacle = new GameObject("Obstacle");

            var renderer = obstacle.AddComponent<SpriteRenderer>();
            renderer.sprite = CreateSquareSprite();
            renderer.color = new Color(0.3f, 0.3f, 0.3f);
            renderer.sortingOrder = 2;
            obstacle.transform.localScale = Vector3.one * 0.8f;

            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(obstacle, path);
            Object.DestroyImmediate(obstacle);

            return prefab;
        }

        private static GameObject CreateLogEntryPrefab()
        {
            string path = $"{PrefabsPath}/UI/LogEntry.prefab";
            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing != null) return existing;

            GameObject entry = new GameObject("LogEntry");

            var rectTransform = entry.AddComponent<RectTransform>();
            rectTransform.sizeDelta = new Vector2(280, 25);

            var text = entry.AddComponent<TextMeshProUGUI>();
            text.fontSize = 12;
            text.alignment = TextAlignmentOptions.Left;
            text.color = Color.white;

            var layoutElement = entry.AddComponent<LayoutElement>();
            layoutElement.preferredHeight = 25;
            layoutElement.flexibleWidth = 1;

            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(entry, path);
            Object.DestroyImmediate(entry);

            return prefab;
        }

        private static GameObject CreateUnitListItemPrefab()
        {
            string path = $"{PrefabsPath}/UI/UnitListItem.prefab";
            GameObject existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing != null) return existing;

            GameObject item = new GameObject("UnitListItem");

            var rectTransform = item.AddComponent<RectTransform>();
            rectTransform.sizeDelta = new Vector2(200, 30);

            var button = item.AddComponent<Button>();
            var image = item.AddComponent<Image>();
            image.color = new Color(0.2f, 0.2f, 0.2f, 0.5f);

            // Text child
            GameObject textObj = new GameObject("Text");
            textObj.transform.SetParent(item.transform);
            var textRect = textObj.AddComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = new Vector2(10, 0);
            textRect.offsetMax = new Vector2(-10, 0);

            var text = textObj.AddComponent<TextMeshProUGUI>();
            text.fontSize = 14;
            text.alignment = TextAlignmentOptions.Left;
            text.color = Color.white;

            var layoutElement = item.AddComponent<LayoutElement>();
            layoutElement.preferredHeight = 30;
            layoutElement.flexibleWidth = 1;

            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(item, path);
            Object.DestroyImmediate(item);

            return prefab;
        }

        #endregion

        #region Sprites

        private static Sprite CreateSquareSprite()
        {
            // Создаём простой белый квадрат
            Texture2D tex = new Texture2D(64, 64);
            Color[] colors = new Color[64 * 64];
            for (int i = 0; i < colors.Length; i++)
            {
                colors[i] = Color.white;
            }
            tex.SetPixels(colors);
            tex.Apply();

            return Sprite.Create(tex, new Rect(0, 0, 64, 64), new Vector2(0.5f, 0.5f), 64);
        }

        private static Sprite CreateCircleSprite()
        {
            Texture2D tex = new Texture2D(64, 64);
            Color[] colors = new Color[64 * 64];
            Vector2 center = new Vector2(32, 32);
            float radius = 30;

            for (int y = 0; y < 64; y++)
            {
                for (int x = 0; x < 64; x++)
                {
                    float dist = Vector2.Distance(new Vector2(x, y), center);
                    colors[y * 64 + x] = dist <= radius ? Color.white : Color.clear;
                }
            }
            tex.SetPixels(colors);
            tex.Apply();

            return Sprite.Create(tex, new Rect(0, 0, 64, 64), new Vector2(0.5f, 0.5f), 64);
        }

        private static Sprite CreateRingSprite()
        {
            Texture2D tex = new Texture2D(64, 64);
            Color[] colors = new Color[64 * 64];
            Vector2 center = new Vector2(32, 32);
            float outerRadius = 30;
            float innerRadius = 26;

            for (int y = 0; y < 64; y++)
            {
                for (int x = 0; x < 64; x++)
                {
                    float dist = Vector2.Distance(new Vector2(x, y), center);
                    colors[y * 64 + x] = (dist <= outerRadius && dist >= innerRadius) ? Color.white : Color.clear;
                }
            }
            tex.SetPixels(colors);
            tex.Apply();

            return Sprite.Create(tex, new Rect(0, 0, 64, 64), new Vector2(0.5f, 0.5f), 64);
        }

        #endregion

        #region Scenes

        private static void CreateBootstrapScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "Bootstrap";

            // Camera
            GameObject camObj = new GameObject("Main Camera");
            var cam = camObj.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = 5;
            cam.backgroundColor = new Color(0.1f, 0.1f, 0.15f);
            cam.clearFlags = CameraClearFlags.SolidColor;
            camObj.tag = "MainCamera";
            camObj.transform.position = new Vector3(0, 0, -10);

            // Bootstrap object
            GameObject bootstrap = new GameObject("GameBootstrap");
            bootstrap.AddComponent<ModernHomm.Core.Bootstrap>();

            // Loading text
            GameObject canvas = CreateCanvas("LoadingCanvas");
            GameObject textObj = CreateText(canvas, "LoadingText", "Загрузка...", 36);
            var textRect = textObj.GetComponent<RectTransform>();
            textRect.anchoredPosition = Vector2.zero;

            EditorSceneManager.SaveScene(scene, $"{ScenesPath}/Bootstrap.unity");
            Debug.Log("[ModernHomm] Создана сцена Bootstrap");
        }

        private static void CreateMainMenuScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "MainMenu";

            // Camera
            GameObject camObj = new GameObject("Main Camera");
            var cam = camObj.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = 5;
            cam.backgroundColor = new Color(0.1f, 0.15f, 0.2f);
            cam.clearFlags = CameraClearFlags.SolidColor;
            camObj.tag = "MainCamera";
            camObj.transform.position = new Vector3(0, 0, -10);

            // Canvas
            GameObject canvas = CreateCanvas("MainMenuCanvas");

            // Title
            GameObject title = CreateText(canvas, "Title", "⚔️ ARENA ⚔️", 48);
            var titleRect = title.GetComponent<RectTransform>();
            titleRect.anchorMin = new Vector2(0.5f, 1);
            titleRect.anchorMax = new Vector2(0.5f, 1);
            titleRect.anchoredPosition = new Vector2(0, -80);

            // Player Panel (Left)
            GameObject playerPanel = CreatePanel(canvas, "PlayerPanel", new Vector2(350, 400));
            var playerRect = playerPanel.GetComponent<RectTransform>();
            playerRect.anchorMin = new Vector2(0, 0.5f);
            playerRect.anchorMax = new Vector2(0, 0.5f);
            playerRect.anchoredPosition = new Vector2(200, 0);

            CreateText(playerPanel, "PlayerNameText", "👤 Игрок", 24);
            CreateText(playerPanel, "BalanceText", "💰 1000", 18);
            CreateText(playerPanel, "ArmyCostText", "⚔️ 500", 18);
            CreateText(playerPanel, "StatsText", "🏆 0 | 💔 0", 18);
            ArrangeVertically(playerPanel, 40);

            // Opponent Panel (Center)
            GameObject opponentPanel = CreatePanel(canvas, "OpponentPanel", new Vector2(400, 300));
            var oppRect = opponentPanel.GetComponent<RectTransform>();
            oppRect.anchorMin = new Vector2(0.5f, 0.5f);
            oppRect.anchorMax = new Vector2(0.5f, 0.5f);
            oppRect.anchoredPosition = new Vector2(0, 0);

            CreateText(opponentPanel, "SelectOpponentLabel", "Выберите противника:", 20);
            GameObject oppDropdown = CreateDropdown(opponentPanel, "OpponentDropdown");
            CreateText(opponentPanel, "OpponentInfoText", "Информация о противнике", 14);
            CreateText(opponentPanel, "FieldSizeLabel", "Размер поля:", 16);
            GameObject fieldDropdown = CreateDropdown(opponentPanel, "FieldSizeDropdown");
            GameObject startBtn = CreateButton(opponentPanel, "StartBattleButton", "⚔️ НАЧАТЬ БОЙ");
            ArrangeVertically(opponentPanel, 45);

            // Status text
            GameObject statusText = CreateText(canvas, "StatusText", "", 16);
            var statusRect = statusText.GetComponent<RectTransform>();
            statusRect.anchorMin = new Vector2(0.5f, 0);
            statusRect.anchorMax = new Vector2(0.5f, 0);
            statusRect.anchoredPosition = new Vector2(0, 50);

            // Pending Game Panel (изначально неактивна)
            GameObject pendingPanel = CreatePanel(canvas, "PendingGamePanel", new Vector2(400, 200));
            var pendingRect = pendingPanel.GetComponent<RectTransform>();
            pendingRect.anchorMin = new Vector2(0.5f, 0.5f);
            pendingRect.anchorMax = new Vector2(0.5f, 0.5f);
            pendingRect.anchoredPosition = new Vector2(0, 200);
            pendingPanel.GetComponent<Image>().color = new Color(0.2f, 0.3f, 0.4f, 0.95f);

            CreateText(pendingPanel, "PendingGameText", "⚔️ Вас вызывают на бой!", 18);
            GameObject acceptBtn = CreateButton(pendingPanel, "AcceptButton", "✅ Принять");
            GameObject declineBtn = CreateButton(pendingPanel, "DeclineButton", "❌ Отклонить");
            declineBtn.GetComponent<Image>().color = new Color(0.6f, 0.2f, 0.2f);
            ArrangeVertically(pendingPanel, 50);
            pendingPanel.SetActive(false);

            // Menu Manager
            GameObject menuManager = new GameObject("MenuManager");
            menuManager.AddComponent<ModernHomm.UI.PlayerSelectUI>();

            EditorSceneManager.SaveScene(scene, $"{ScenesPath}/MainMenu.unity");
            Debug.Log("[ModernHomm] Создана сцена MainMenu");
        }

        private static void CreateBattleScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "Battle";

            // Camera
            GameObject camObj = new GameObject("Main Camera");
            var cam = camObj.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = 6;
            cam.backgroundColor = new Color(0.15f, 0.15f, 0.2f);
            cam.clearFlags = CameraClearFlags.SolidColor;
            camObj.tag = "MainCamera";
            camObj.transform.position = new Vector3(0, 0, -10);

            // Board
            GameObject board = new GameObject("Board");
            var boardController = board.AddComponent<ModernHomm.Board.BoardController>();

            // Canvas
            GameObject canvas = CreateCanvas("BattleCanvas");

            // Top Panel - Turn Indicator
            GameObject topPanel = CreatePanel(canvas, "TopPanel", new Vector2(400, 60));
            var topRect = topPanel.GetComponent<RectTransform>();
            topRect.anchorMin = new Vector2(0.5f, 1);
            topRect.anchorMax = new Vector2(0.5f, 1);
            topRect.anchoredPosition = new Vector2(0, -40);
            topPanel.GetComponent<Image>().color = new Color(0.2f, 0.6f, 0.2f);

            GameObject turnText = CreateText(topPanel, "TurnIndicatorText", "⚔️ ВАШ ХОД!", 24);
            var turnRect = turnText.GetComponent<RectTransform>();
            turnRect.anchorMin = Vector2.zero;
            turnRect.anchorMax = Vector2.one;
            turnRect.offsetMin = Vector2.zero;
            turnRect.offsetMax = Vector2.zero;

            // Left Panel - Player 1
            GameObject leftPanel = CreatePanel(canvas, "Player1Panel", new Vector2(250, 500));
            var leftRect = leftPanel.GetComponent<RectTransform>();
            leftRect.anchorMin = new Vector2(0, 0.5f);
            leftRect.anchorMax = new Vector2(0, 0.5f);
            leftRect.anchoredPosition = new Vector2(140, 0);
            leftPanel.AddComponent<ModernHomm.UI.UnitInfoPanel>();

            CreateText(leftPanel, "PlayerNameText", "👤 Игрок 1", 20);
            GameObject portraitPanel = CreatePanel(leftPanel, "PortraitPanel", new Vector2(200, 150));
            CreateText(portraitPanel, "UnitIconText", "⚔️", 36);
            CreateText(portraitPanel, "UnitNameText", "Мечник", 16);
            CreateText(portraitPanel, "UnitDamageText", "⚔️ 10", 12);
            CreateText(portraitPanel, "UnitDefenseText", "🛡️ 5", 12);
            CreateText(portraitPanel, "UnitHealthText", "❤️ 100", 12);
            CreateText(portraitPanel, "UnitCountText", "📍 x5", 12);
            ArrangeVertically(portraitPanel, 25);

            // Unit List
            GameObject unitListScroll = CreateScrollView(leftPanel, "UnitListScroll", new Vector2(220, 200));

            // Right Panel - Player 2
            GameObject rightPanel = CreatePanel(canvas, "Player2Panel", new Vector2(250, 500));
            var rightRect = rightPanel.GetComponent<RectTransform>();
            rightRect.anchorMin = new Vector2(1, 0.5f);
            rightRect.anchorMax = new Vector2(1, 0.5f);
            rightRect.anchoredPosition = new Vector2(-140, 0);
            rightPanel.AddComponent<ModernHomm.UI.UnitInfoPanel>();

            CreateText(rightPanel, "PlayerNameText", "👤 Игрок 2", 20);

            // Bottom Panel - Actions
            GameObject bottomPanel = CreatePanel(canvas, "BottomPanel", new Vector2(800, 80));
            var bottomRect = bottomPanel.GetComponent<RectTransform>();
            bottomRect.anchorMin = new Vector2(0.5f, 0);
            bottomRect.anchorMax = new Vector2(0.5f, 0);
            bottomRect.anchoredPosition = new Vector2(0, 50);

            GameObject actionPanel = new GameObject("ActionPanel");
            actionPanel.transform.SetParent(bottomPanel.transform);
            var actionRect = actionPanel.AddComponent<RectTransform>();
            actionRect.anchorMin = Vector2.zero;
            actionRect.anchorMax = Vector2.one;
            actionRect.offsetMin = Vector2.zero;
            actionRect.offsetMax = Vector2.zero;
            var actionLayout = actionPanel.AddComponent<HorizontalLayoutGroup>();
            actionLayout.spacing = 10;
            actionLayout.childAlignment = TextAnchor.MiddleCenter;
            actionPanel.AddComponent<ModernHomm.UI.ActionPanel>();

            CreateButton(actionPanel, "MoveButton", "🚶 Двигаться");
            CreateButton(actionPanel, "AttackButton", "⚔️ Атаковать");
            CreateButton(actionPanel, "SkipButton", "⏭️ Пропустить");
            CreateButton(actionPanel, "DeferButton", "⏸️ Отложить");
            GameObject surrenderBtn = CreateButton(actionPanel, "SurrenderButton", "🏳️ Сдаться");
            surrenderBtn.GetComponent<Image>().color = new Color(0.5f, 0.2f, 0.2f);

            // Hint text
            GameObject hintText = CreateText(canvas, "HintText", "🎮 Выберите юнита для действия", 16);
            var hintRect = hintText.GetComponent<RectTransform>();
            hintRect.anchorMin = new Vector2(0.5f, 0);
            hintRect.anchorMax = new Vector2(0.5f, 0);
            hintRect.anchoredPosition = new Vector2(0, 110);

            // Game Log Panel (Right side)
            GameObject logPanel = CreatePanel(canvas, "GameLogPanel", new Vector2(300, 300));
            var logRect = logPanel.GetComponent<RectTransform>();
            logRect.anchorMin = new Vector2(1, 0);
            logRect.anchorMax = new Vector2(1, 0);
            logRect.anchoredPosition = new Vector2(-170, 200);
            logPanel.GetComponent<Image>().color = new Color(0.1f, 0.1f, 0.1f, 0.8f);
            logPanel.AddComponent<ModernHomm.UI.GameLogUI>();

            CreateText(logPanel, "LogTitle", "📜 Журнал боя", 16);
            GameObject logScroll = CreateScrollView(logPanel, "LogScrollView", new Vector2(280, 250));

            // Overlays
            GameObject overlays = new GameObject("Overlays");
            overlays.transform.SetParent(canvas.transform);
            var overlaysRect = overlays.AddComponent<RectTransform>();
            overlaysRect.anchorMin = Vector2.zero;
            overlaysRect.anchorMax = Vector2.one;
            overlaysRect.offsetMin = Vector2.zero;
            overlaysRect.offsetMax = Vector2.zero;
            overlays.AddComponent<ModernHomm.UI.OverlayUI>();

            // Battle Result Panel
            GameObject battleResultPanel = CreatePanel(overlays, "BattleResultPanel", new Vector2(500, 200));
            battleResultPanel.GetComponent<Image>().color = new Color(0, 0, 0, 0.9f);
            var battleResultCG = battleResultPanel.AddComponent<CanvasGroup>();
            CreateText(battleResultPanel, "BattleResultText", "⚔️ Результат атаки", 20);
            battleResultPanel.SetActive(false);

            // Game Over Panel
            GameObject gameOverPanel = CreatePanel(overlays, "GameOverPanel", new Vector2(600, 400));
            gameOverPanel.GetComponent<Image>().color = new Color(0, 0, 0, 0.95f);
            CreateText(gameOverPanel, "GameOverTitle", "🏆 ПОБЕДА!", 48);
            CreateText(gameOverPanel, "GameOverSubtitle", "Вы одержали победу!", 24);
            CreateText(gameOverPanel, "GameOverStats", "Статистика боя...", 16);
            CreateButton(gameOverPanel, "ReturnButton", "🏠 Вернуться в меню");
            ArrangeVertically(gameOverPanel, 60);
            gameOverPanel.SetActive(false);

            // GameBoard UI Manager
            GameObject gameBoardUI = new GameObject("GameBoardUI");
            gameBoardUI.AddComponent<ModernHomm.UI.GameBoardUI>();

            EditorSceneManager.SaveScene(scene, $"{ScenesPath}/Battle.unity");
            Debug.Log("[ModernHomm] Создана сцена Battle");
        }

        #endregion

        #region UI Helpers

        private static GameObject CreateCanvas(string name)
        {
            GameObject canvasObj = new GameObject(name);

            var canvas = canvasObj.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;

            var scaler = canvasObj.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 0.5f;

            canvasObj.AddComponent<GraphicRaycaster>();

            return canvasObj;
        }

        private static GameObject CreatePanel(GameObject parent, string name, Vector2 size)
        {
            GameObject panel = new GameObject(name);
            panel.transform.SetParent(parent.transform);

            var rect = panel.AddComponent<RectTransform>();
            rect.sizeDelta = size;

            var image = panel.AddComponent<Image>();
            image.color = new Color(0.15f, 0.15f, 0.2f, 0.9f);

            return panel;
        }

        private static GameObject CreateText(GameObject parent, string name, string text, int fontSize)
        {
            GameObject textObj = new GameObject(name);
            textObj.transform.SetParent(parent.transform);

            var rect = textObj.AddComponent<RectTransform>();
            rect.sizeDelta = new Vector2(300, 40);

            var tmp = textObj.AddComponent<TextMeshProUGUI>();
            tmp.text = text;
            tmp.fontSize = fontSize;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.color = Color.white;

            return textObj;
        }

        private static GameObject CreateButton(GameObject parent, string name, string text)
        {
            GameObject btnObj = new GameObject(name);
            btnObj.transform.SetParent(parent.transform);

            var rect = btnObj.AddComponent<RectTransform>();
            rect.sizeDelta = new Vector2(150, 40);

            var image = btnObj.AddComponent<Image>();
            image.color = new Color(0.2f, 0.4f, 0.6f);

            var button = btnObj.AddComponent<Button>();
            var colors = button.colors;
            colors.highlightedColor = new Color(0.3f, 0.5f, 0.7f);
            colors.pressedColor = new Color(0.15f, 0.3f, 0.5f);
            button.colors = colors;

            // Text child
            GameObject textObj = new GameObject("Text");
            textObj.transform.SetParent(btnObj.transform);

            var textRect = textObj.AddComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = Vector2.zero;
            textRect.offsetMax = Vector2.zero;

            var tmp = textObj.AddComponent<TextMeshProUGUI>();
            tmp.text = text;
            tmp.fontSize = 16;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.color = Color.white;

            return btnObj;
        }

        private static GameObject CreateDropdown(GameObject parent, string name)
        {
            GameObject ddObj = new GameObject(name);
            ddObj.transform.SetParent(parent.transform);

            var rect = ddObj.AddComponent<RectTransform>();
            rect.sizeDelta = new Vector2(300, 35);

            var image = ddObj.AddComponent<Image>();
            image.color = new Color(0.2f, 0.2f, 0.25f);

            var dropdown = ddObj.AddComponent<TMP_Dropdown>();

            // Label
            GameObject label = new GameObject("Label");
            label.transform.SetParent(ddObj.transform);
            var labelRect = label.AddComponent<RectTransform>();
            labelRect.anchorMin = Vector2.zero;
            labelRect.anchorMax = Vector2.one;
            labelRect.offsetMin = new Vector2(10, 0);
            labelRect.offsetMax = new Vector2(-30, 0);
            var labelText = label.AddComponent<TextMeshProUGUI>();
            labelText.text = "Выберите...";
            labelText.fontSize = 14;
            labelText.alignment = TextAlignmentOptions.Left;

            dropdown.captionText = labelText;

            // Template (простой - Unity создаст остальное)
            GameObject template = new GameObject("Template");
            template.transform.SetParent(ddObj.transform);
            template.SetActive(false);

            return ddObj;
        }

        private static GameObject CreateScrollView(GameObject parent, string name, Vector2 size)
        {
            GameObject scrollObj = new GameObject(name);
            scrollObj.transform.SetParent(parent.transform);

            var rect = scrollObj.AddComponent<RectTransform>();
            rect.sizeDelta = size;

            var scrollRect = scrollObj.AddComponent<ScrollRect>();

            // Viewport
            GameObject viewport = new GameObject("Viewport");
            viewport.transform.SetParent(scrollObj.transform);
            var viewRect = viewport.AddComponent<RectTransform>();
            viewRect.anchorMin = Vector2.zero;
            viewRect.anchorMax = Vector2.one;
            viewRect.offsetMin = Vector2.zero;
            viewRect.offsetMax = Vector2.zero;
            viewport.AddComponent<Image>().color = new Color(0, 0, 0, 0);
            viewport.AddComponent<Mask>().showMaskGraphic = false;

            // Content
            GameObject content = new GameObject("Content");
            content.transform.SetParent(viewport.transform);
            var contentRect = content.AddComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0, 1);
            contentRect.anchorMax = new Vector2(1, 1);
            contentRect.pivot = new Vector2(0.5f, 1);
            contentRect.sizeDelta = new Vector2(0, 0);

            var layout = content.AddComponent<VerticalLayoutGroup>();
            layout.childForceExpandHeight = false;
            layout.childControlHeight = false;
            layout.spacing = 5;

            var fitter = content.AddComponent<ContentSizeFitter>();
            fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

            scrollRect.viewport = viewRect;
            scrollRect.content = contentRect;
            scrollRect.horizontal = false;
            scrollRect.vertical = true;

            return scrollObj;
        }

        private static void ArrangeVertically(GameObject parent, float spacing)
        {
            var layout = parent.GetComponent<VerticalLayoutGroup>();
            if (layout == null)
            {
                layout = parent.AddComponent<VerticalLayoutGroup>();
            }

            layout.childAlignment = TextAnchor.UpperCenter;
            layout.childForceExpandWidth = false;
            layout.childForceExpandHeight = false;
            layout.spacing = spacing;
            layout.padding = new RectOffset(10, 10, 20, 20);
        }

        #endregion

        #region Build Settings

        private static void SetupBuildSettings()
        {
            var scenes = new EditorBuildSettingsScene[]
            {
                new EditorBuildSettingsScene($"{ScenesPath}/Bootstrap.unity", true),
                new EditorBuildSettingsScene($"{ScenesPath}/MainMenu.unity", true),
                new EditorBuildSettingsScene($"{ScenesPath}/Battle.unity", true),
            };

            EditorBuildSettings.scenes = scenes;
            Debug.Log("[ModernHomm] Build Settings обновлены");
        }

        #endregion
    }
}
