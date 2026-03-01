var __read = (this && this.__read) || function (o, n) {
    var m = typeof Symbol === "function" && o[Symbol.iterator];
    if (!m) return o;
    var i = m.call(o), r, ar = [], e;
    try {
        while ((n === void 0 || n-- > 0) && !(r = i.next()).done) ar.push(r.value);
    }
    catch (error) { e = { error: error }; }
    finally {
        try {
            if (r && !r.done && (m = i["return"])) m.call(i);
        }
        finally { if (e) throw e.error; }
    }
    return ar;
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
import { errorToProperties, unhandledRejectionToProperties } from '../extensions/exception-autocapture/error-conversion';
import { assignableWindow, window } from '../utils/globals';
import { logger } from '../utils/logger';
var wrapOnError = function (captureFn) {
    var win = window;
    if (!win) {
        logger.info('window not available, cannot wrap onerror');
    }
    var originalOnError = win.onerror;
    win.onerror = function () {
        var _a;
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
            args[_i] = arguments[_i];
        }
        var errorProperties = errorToProperties(args);
        captureFn(errorProperties);
        return (_a = originalOnError === null || originalOnError === void 0 ? void 0 : originalOnError.apply(void 0, __spreadArray([], __read(args), false))) !== null && _a !== void 0 ? _a : false;
    };
    win.onerror.__POSTHOG_INSTRUMENTED__ = true;
    return function () {
        var _a;
        (_a = win.onerror) === null || _a === void 0 ? true : delete _a.__POSTHOG_INSTRUMENTED__;
        win.onerror = originalOnError;
    };
};
var wrapUnhandledRejection = function (captureFn) {
    var win = window;
    if (!win) {
        logger.info('window not available, cannot wrap onUnhandledRejection');
    }
    var originalOnUnhandledRejection = win.onunhandledrejection;
    win.onunhandledrejection = function () {
        var _a;
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
            args[_i] = arguments[_i];
        }
        var errorProperties = unhandledRejectionToProperties(args);
        captureFn(errorProperties);
        return (_a = originalOnUnhandledRejection === null || originalOnUnhandledRejection === void 0 ? void 0 : originalOnUnhandledRejection.apply(win, args)) !== null && _a !== void 0 ? _a : false;
    };
    win.onunhandledrejection.__POSTHOG_INSTRUMENTED__ = true;
    return function () {
        var _a;
        (_a = win.onunhandledrejection) === null || _a === void 0 ? true : delete _a.__POSTHOG_INSTRUMENTED__;
        win.onunhandledrejection = originalOnUnhandledRejection;
    };
};
var posthogErrorWrappingFunctions = {
    wrapOnError: wrapOnError,
    wrapUnhandledRejection: wrapUnhandledRejection,
};
assignableWindow.__PosthogExtensions__ = assignableWindow.__PosthogExtensions__ || {};
assignableWindow.__PosthogExtensions__.errorWrappingFunctions = posthogErrorWrappingFunctions;
assignableWindow.__PosthogExtensions__.parseErrorAsProperties = errorToProperties;
// we used to put these on window, and now we put them on __PosthogExtensions__
// but that means that old clients which lazily load this extension are looking in the wrong place
// yuck,
// so we also put them directly on the window
// when 1.161.1 is the oldest version seen in production we can remove this
assignableWindow.posthogErrorWrappingFunctions = posthogErrorWrappingFunctions;
assignableWindow.parseErrorAsProperties = errorToProperties;
export default posthogErrorWrappingFunctions;
//# sourceMappingURL=exception-autocapture.js.map