mergeInto(LibraryManager.library, {
    GetUrlParam: function(paramName) {
        var paramNameStr = UTF8ToString(paramName);
        var urlParams = new URLSearchParams(window.location.search);
        var value = urlParams.get(paramNameStr);
        if (value === null) {
            return null;
        }
        var bufferSize = lengthBytesUTF8(value) + 1;
        var buffer = _malloc(bufferSize);
        stringToUTF8(value, buffer, bufferSize);
        return buffer;
    },

    SetLocalStorage: function(key, value) {
        var keyStr = UTF8ToString(key);
        var valueStr = UTF8ToString(value);
        try {
            localStorage.setItem(keyStr, valueStr);
        } catch (e) {
            console.warn('LocalStorage not available:', e);
        }
    },

    GetLocalStorage: function(key) {
        var keyStr = UTF8ToString(key);
        try {
            var value = localStorage.getItem(keyStr);
            if (value === null) {
                return null;
            }
            var bufferSize = lengthBytesUTF8(value) + 1;
            var buffer = _malloc(bufferSize);
            stringToUTF8(value, buffer, bufferSize);
            return buffer;
        } catch (e) {
            console.warn('LocalStorage not available:', e);
            return null;
        }
    },

    RemoveLocalStorage: function(key) {
        var keyStr = UTF8ToString(key);
        try {
            localStorage.removeItem(keyStr);
        } catch (e) {
            console.warn('LocalStorage not available:', e);
        }
    },

    GetCurrentUrl: function() {
        var url = window.location.href;
        var bufferSize = lengthBytesUTF8(url) + 1;
        var buffer = _malloc(bufferSize);
        stringToUTF8(url, buffer, bufferSize);
        return buffer;
    },

    RedirectTo: function(url) {
        var urlStr = UTF8ToString(url);
        window.location.href = urlStr;
    }
});
