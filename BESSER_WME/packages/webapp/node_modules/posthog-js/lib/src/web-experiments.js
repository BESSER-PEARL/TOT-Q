import { navigator, window } from './utils/globals';
import { WEB_EXPERIMENTS } from './constants';
import { isNullish } from './utils/type-utils';
import { getQueryParam, isUrlMatchingRegex } from './utils/request-utils';
import { logger } from './utils/logger';
import { Info } from './utils/event-utils';
import { isLikelyBot } from './utils/blocked-uas';
export var webExperimentUrlValidationMap = {
    icontains: function (conditionsUrl, location) {
        return !!window && location.href.toLowerCase().indexOf(conditionsUrl.toLowerCase()) > -1;
    },
    not_icontains: function (conditionsUrl, location) {
        return !!window && location.href.toLowerCase().indexOf(conditionsUrl.toLowerCase()) === -1;
    },
    regex: function (conditionsUrl, location) { return !!window && isUrlMatchingRegex(location.href, conditionsUrl); },
    not_regex: function (conditionsUrl, location) { return !!window && !isUrlMatchingRegex(location.href, conditionsUrl); },
    exact: function (conditionsUrl, location) { return location.href === conditionsUrl; },
    is_not: function (conditionsUrl, location) { return location.href !== conditionsUrl; },
};
var WebExperiments = /** @class */ (function () {
    function WebExperiments(instance) {
        var _this = this;
        this.getWebExperimentsAndEvaluateDisplayLogic = function (forceReload) {
            if (forceReload === void 0) { forceReload = false; }
            _this.getWebExperiments(function (webExperiments) {
                WebExperiments.logInfo("retrieved web experiments from the server");
                _this._flagToExperiments = new Map();
                webExperiments.forEach(function (webExperiment) {
                    var _a;
                    if (webExperiment.feature_flag_key &&
                        _this._featureFlags &&
                        _this._featureFlags[webExperiment.feature_flag_key]) {
                        if (_this._flagToExperiments) {
                            WebExperiments.logInfo("setting flag key ", webExperiment.feature_flag_key, " to web experiment ", webExperiment);
                            (_a = _this._flagToExperiments) === null || _a === void 0 ? void 0 : _a.set(webExperiment.feature_flag_key, webExperiment);
                        }
                        var selectedVariant = _this._featureFlags[webExperiment.feature_flag_key];
                        if (selectedVariant && webExperiment.variants[selectedVariant]) {
                            _this.applyTransforms(webExperiment.name, selectedVariant, webExperiment.variants[selectedVariant].transforms);
                        }
                    }
                    else if (webExperiment.variants) {
                        for (var variant in webExperiment.variants) {
                            var testVariant = webExperiment.variants[variant];
                            var matchTest = WebExperiments.matchesTestVariant(testVariant);
                            if (matchTest) {
                                _this.applyTransforms(webExperiment.name, variant, testVariant.transforms);
                            }
                        }
                    }
                });
            }, forceReload);
        };
        this.instance = instance;
        var appFeatureFLags = function (flags) {
            _this.applyFeatureFlagChanges(flags);
        };
        if (this.instance.onFeatureFlags) {
            this.instance.onFeatureFlags(appFeatureFLags);
        }
        this._flagToExperiments = new Map();
    }
    WebExperiments.prototype.applyFeatureFlagChanges = function (flags) {
        var _this = this;
        if (isNullish(this._flagToExperiments) || this.instance.config.disable_web_experiments) {
            return;
        }
        WebExperiments.logInfo('applying feature flags', flags);
        flags.forEach(function (flag) {
            var _a, _b;
            if (_this._flagToExperiments && ((_a = _this._flagToExperiments) === null || _a === void 0 ? void 0 : _a.has(flag))) {
                var selectedVariant = _this.instance.getFeatureFlag(flag);
                var webExperiment = (_b = _this._flagToExperiments) === null || _b === void 0 ? void 0 : _b.get(flag);
                if (selectedVariant && (webExperiment === null || webExperiment === void 0 ? void 0 : webExperiment.variants[selectedVariant])) {
                    _this.applyTransforms(webExperiment.name, selectedVariant, webExperiment.variants[selectedVariant].transforms);
                }
            }
        });
    };
    WebExperiments.prototype.afterDecideResponse = function (response) {
        if (this._is_bot()) {
            WebExperiments.logInfo('Refusing to render web experiment since the viewer is a likely bot');
            return;
        }
        this._featureFlags = response.featureFlags;
        this.loadIfEnabled();
        this.previewWebExperiment();
    };
    WebExperiments.prototype.previewWebExperiment = function () {
        var _this = this;
        var location = WebExperiments.getWindowLocation();
        if (location === null || location === void 0 ? void 0 : location.search) {
            var experimentID_1 = getQueryParam(location === null || location === void 0 ? void 0 : location.search, '__experiment_id');
            var variant_1 = getQueryParam(location === null || location === void 0 ? void 0 : location.search, '__experiment_variant');
            if (experimentID_1 && variant_1) {
                WebExperiments.logInfo("previewing web experiments ".concat(experimentID_1, " && ").concat(variant_1));
                this.getWebExperiments(function (webExperiments) {
                    _this.showPreviewWebExperiment(parseInt(experimentID_1), variant_1, webExperiments);
                }, false, true);
            }
        }
    };
    WebExperiments.prototype.loadIfEnabled = function () {
        if (this.instance.config.disable_web_experiments) {
            return;
        }
        this.getWebExperimentsAndEvaluateDisplayLogic();
    };
    WebExperiments.prototype.getWebExperiments = function (callback, forceReload, previewing) {
        if (this.instance.config.disable_web_experiments && !previewing) {
            return callback([]);
        }
        var existingWebExperiments = this.instance.get_property(WEB_EXPERIMENTS);
        if (existingWebExperiments && !forceReload) {
            return callback(existingWebExperiments);
        }
        this.instance._send_request({
            url: this.instance.requestRouter.endpointFor('api', "/api/web_experiments/?token=".concat(this.instance.config.token)),
            method: 'GET',
            transport: 'XHR',
            callback: function (response) {
                if (response.statusCode !== 200 || !response.json) {
                    return callback([]);
                }
                var webExperiments = response.json.experiments || [];
                return callback(webExperiments);
            },
        });
    };
    WebExperiments.prototype.showPreviewWebExperiment = function (experimentID, variant, webExperiments) {
        var previewExperiments = webExperiments.filter(function (exp) { return exp.id === experimentID; });
        if (previewExperiments && previewExperiments.length > 0) {
            WebExperiments.logInfo("Previewing web experiment [".concat(previewExperiments[0].name, "] with variant [").concat(variant, "]"));
            this.applyTransforms(previewExperiments[0].name, variant, previewExperiments[0].variants[variant].transforms, true);
        }
    };
    WebExperiments.matchesTestVariant = function (testVariant) {
        if (isNullish(testVariant.conditions)) {
            return false;
        }
        return WebExperiments.matchUrlConditions(testVariant) && WebExperiments.matchUTMConditions(testVariant);
    };
    WebExperiments.matchUrlConditions = function (testVariant) {
        var _a, _b, _c, _d;
        if (isNullish(testVariant.conditions) || isNullish((_a = testVariant.conditions) === null || _a === void 0 ? void 0 : _a.url)) {
            return true;
        }
        var location = WebExperiments.getWindowLocation();
        if (location) {
            var urlCheck = ((_b = testVariant.conditions) === null || _b === void 0 ? void 0 : _b.url)
                ? webExperimentUrlValidationMap[(_d = (_c = testVariant.conditions) === null || _c === void 0 ? void 0 : _c.urlMatchType) !== null && _d !== void 0 ? _d : 'icontains'](testVariant.conditions.url, location)
                : true;
            return urlCheck;
        }
        return false;
    };
    WebExperiments.getWindowLocation = function () {
        return window === null || window === void 0 ? void 0 : window.location;
    };
    WebExperiments.matchUTMConditions = function (testVariant) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p, _q, _r, _s;
        if (isNullish(testVariant.conditions) || isNullish((_a = testVariant.conditions) === null || _a === void 0 ? void 0 : _a.utm)) {
            return true;
        }
        var campaignParams = Info.campaignParams();
        if (campaignParams['utm_source']) {
            // eslint-disable-next-line compat/compat
            var utmCampaignMatched = ((_c = (_b = testVariant.conditions) === null || _b === void 0 ? void 0 : _b.utm) === null || _c === void 0 ? void 0 : _c.utm_campaign)
                ? ((_e = (_d = testVariant.conditions) === null || _d === void 0 ? void 0 : _d.utm) === null || _e === void 0 ? void 0 : _e.utm_campaign) == campaignParams['utm_campaign']
                : true;
            var utmSourceMatched = ((_g = (_f = testVariant.conditions) === null || _f === void 0 ? void 0 : _f.utm) === null || _g === void 0 ? void 0 : _g.utm_source)
                ? ((_j = (_h = testVariant.conditions) === null || _h === void 0 ? void 0 : _h.utm) === null || _j === void 0 ? void 0 : _j.utm_source) == campaignParams['utm_source']
                : true;
            var utmMediumMatched = ((_l = (_k = testVariant.conditions) === null || _k === void 0 ? void 0 : _k.utm) === null || _l === void 0 ? void 0 : _l.utm_medium)
                ? ((_o = (_m = testVariant.conditions) === null || _m === void 0 ? void 0 : _m.utm) === null || _o === void 0 ? void 0 : _o.utm_medium) == campaignParams['utm_medium']
                : true;
            var utmTermMatched = ((_q = (_p = testVariant.conditions) === null || _p === void 0 ? void 0 : _p.utm) === null || _q === void 0 ? void 0 : _q.utm_term)
                ? ((_s = (_r = testVariant.conditions) === null || _r === void 0 ? void 0 : _r.utm) === null || _s === void 0 ? void 0 : _s.utm_term) == campaignParams['utm_term']
                : true;
            return utmCampaignMatched && utmMediumMatched && utmTermMatched && utmSourceMatched;
        }
        return false;
    };
    WebExperiments.logInfo = function (msg) {
        var args = [];
        for (var _i = 1; _i < arguments.length; _i++) {
            args[_i - 1] = arguments[_i];
        }
        logger.info("[WebExperiments] ".concat(msg), args);
    };
    WebExperiments.prototype.applyTransforms = function (experiment, variant, transforms, isPreview) {
        var _this = this;
        var _a;
        if (this._is_bot()) {
            WebExperiments.logInfo('Refusing to render web experiment since the viewer is a likely bot');
            return;
        }
        if (variant === 'control') {
            WebExperiments.logInfo('Control variants leave the page unmodified.');
            if (this.instance && this.instance.capture) {
                this.instance.capture('$web_experiment_applied', {
                    $web_experiment_name: experiment,
                    $web_experiment_preview: isPreview,
                    $web_experiment_variant: variant,
                    $web_experiment_document_url: (_a = WebExperiments.getWindowLocation()) === null || _a === void 0 ? void 0 : _a.href,
                    $web_experiment_elements_modified: 0,
                });
            }
            return;
        }
        transforms.forEach(function (transform) {
            var _a;
            if (transform.selector) {
                WebExperiments.logInfo("applying transform of variant ".concat(variant, " for experiment ").concat(experiment, " "), transform);
                var elementsModified_1 = 0;
                // eslint-disable-next-line no-restricted-globals
                var elements = document === null || document === void 0 ? void 0 : document.querySelectorAll(transform.selector);
                elements === null || elements === void 0 ? void 0 : elements.forEach(function (element) {
                    var htmlElement = element;
                    elementsModified_1 += 1;
                    if (transform.attributes) {
                        transform.attributes.forEach(function (attribute) {
                            switch (attribute.name) {
                                case 'text':
                                    htmlElement.innerText = attribute.value;
                                    break;
                                case 'html':
                                    htmlElement.innerHTML = attribute.value;
                                    break;
                                case 'cssClass':
                                    htmlElement.className = attribute.value;
                                    break;
                                default:
                                    htmlElement.setAttribute(attribute.name, attribute.value);
                            }
                        });
                    }
                    if (transform.text) {
                        htmlElement.innerText = transform.text;
                    }
                    if (transform.html) {
                        if (htmlElement.parentElement) {
                            htmlElement.parentElement.innerHTML = transform.html;
                        }
                        else {
                            htmlElement.innerHTML = transform.html;
                        }
                    }
                    if (transform.css) {
                        htmlElement.setAttribute('style', transform.css);
                    }
                });
                if (_this.instance && _this.instance.capture) {
                    _this.instance.capture('$web_experiment_applied', {
                        $web_experiment_name: experiment,
                        $web_experiment_variant: variant,
                        $web_experiment_preview: isPreview,
                        $web_experiment_document_url: (_a = WebExperiments.getWindowLocation()) === null || _a === void 0 ? void 0 : _a.href,
                        $web_experiment_elements_modified: elementsModified_1,
                    });
                }
            }
        });
    };
    WebExperiments.prototype._is_bot = function () {
        if (navigator && this.instance) {
            return isLikelyBot(navigator, this.instance.config.custom_blocked_useragents);
        }
        else {
            return undefined;
        }
    };
    return WebExperiments;
}());
export { WebExperiments };
//# sourceMappingURL=web-experiments.js.map