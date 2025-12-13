mergeInto(LibraryManager.library, {
    // URL Parameters
    GetUrlParam: function(paramNamePtr) {
        var paramName = UTF8ToString(paramNamePtr);
        var urlParams = new URLSearchParams(window.location.search);
        var value = urlParams.get(paramName) || '';
        var bufferSize = lengthBytesUTF8(value) + 1;
        var buffer = _malloc(bufferSize);
        stringToUTF8(value, buffer, bufferSize);
        return buffer;
    },

    // LocalStorage
    SetLocalStorage: function(keyPtr, valuePtr) {
        var key = UTF8ToString(keyPtr);
        var value = UTF8ToString(valuePtr);
        try {
            localStorage.setItem(key, value);
        } catch (e) {
            console.warn('LocalStorage error:', e);
        }
    },

    GetLocalStorage: function(keyPtr) {
        var key = UTF8ToString(keyPtr);
        var value = '';
        try {
            value = localStorage.getItem(key) || '';
        } catch (e) {
            console.warn('LocalStorage error:', e);
        }
        var bufferSize = lengthBytesUTF8(value) + 1;
        var buffer = _malloc(bufferSize);
        stringToUTF8(value, buffer, bufferSize);
        return buffer;
    },

    RemoveLocalStorage: function(keyPtr) {
        var key = UTF8ToString(keyPtr);
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.warn('LocalStorage error:', e);
        }
    },

    // URL & Navigation
    GetCurrentUrl: function() {
        var value = window.location.href;
        var bufferSize = lengthBytesUTF8(value) + 1;
        var buffer = _malloc(bufferSize);
        stringToUTF8(value, buffer, bufferSize);
        return buffer;
    },

    RedirectTo: function(urlPtr) {
        var url = UTF8ToString(urlPtr);
        window.location.href = url;
    },

    // UI Updates - Turn Indicator
    JS_UpdateTurnIndicator: function(textPtr, isMyTurn) {
        var text = UTF8ToString(textPtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.updateTurnIndicator) {
            UnityBridge.updateTurnIndicator(text, isMyTurn);
        }
    },

    // UI Updates - Hint
    JS_UpdateHint: function(textPtr) {
        var text = UTF8ToString(textPtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.updateHint) {
            UnityBridge.updateHint(text);
        }
    },

    // UI Updates - Player Info
    JS_UpdatePlayer1Info: function(namePtr, statsPtr) {
        var name = UTF8ToString(namePtr);
        var stats = UTF8ToString(statsPtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.updatePlayer1Info) {
            UnityBridge.updatePlayer1Info(name, stats);
        }
    },

    JS_UpdatePlayer2Info: function(namePtr, statsPtr) {
        var name = UTF8ToString(namePtr);
        var stats = UTF8ToString(statsPtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.updatePlayer2Info) {
            UnityBridge.updatePlayer2Info(name, stats);
        }
    },

    JS_SetPlayerActive: function(playerNum) {
        if (typeof UnityBridge !== 'undefined' && UnityBridge.setPlayerActive) {
            UnityBridge.setPlayerActive(playerNum);
        }
    },

    // UI Updates - Action Buttons
    JS_EnableActionButtons: function(canMove, canAttack, canSkip, canDefer) {
        if (typeof UnityBridge !== 'undefined' && UnityBridge.enableActionButtons) {
            UnityBridge.enableActionButtons(canMove, canAttack, canSkip, canDefer);
        }
    },

    JS_DisableAllActionButtons: function() {
        if (typeof UnityBridge !== 'undefined' && UnityBridge.disableAllActionButtons) {
            UnityBridge.disableAllActionButtons();
        }
    },

    // UI Updates - Log
    JS_AddLogEntry: function(messagePtr, typePtr) {
        var message = UTF8ToString(messagePtr);
        var type = UTF8ToString(typePtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.addLogEntry) {
            UnityBridge.addLogEntry(message, type);
        }
    },

    JS_ClearLog: function() {
        if (typeof UnityBridge !== 'undefined' && UnityBridge.clearLog) {
            UnityBridge.clearLog();
        }
    },

    // Battle Overlay
    JS_ShowBattleOverlay: function(attackerNamePtr, attackerImagePtr, targetNamePtr, targetImagePtr, resultTextPtr) {
        var attackerName = UTF8ToString(attackerNamePtr);
        var attackerImage = UTF8ToString(attackerImagePtr);
        var targetName = UTF8ToString(targetNamePtr);
        var targetImage = UTF8ToString(targetImagePtr);
        var resultText = UTF8ToString(resultTextPtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.showBattleOverlay) {
            UnityBridge.showBattleOverlay(attackerName, attackerImage, targetName, targetImage, resultText);
        }
    },

    JS_CloseBattleOverlay: function() {
        if (typeof UnityBridge !== 'undefined' && UnityBridge.closeBattleOverlay) {
            UnityBridge.closeBattleOverlay();
        }
    },

    // Game Over
    JS_ShowGameOver: function(isWinner, winnerNamePtr) {
        var winnerName = UTF8ToString(winnerNamePtr);
        if (typeof UnityBridge !== 'undefined' && UnityBridge.showGameOver) {
            UnityBridge.showGameOver(isWinner, winnerName);
        }
    }
});
