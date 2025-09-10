"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var BASE = process.env.BASE_URL || 'http://localhost:8000';
var _fetch = null;
function getFetch() {
    return __awaiter(this, void 0, void 0, function () {
        var mod;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    if (_fetch)
                        return [2 /*return*/, _fetch];
                    return [4 /*yield*/, Promise.resolve().then(function () { return require('node-fetch'); })];
                case 1:
                    mod = _a.sent();
                    _fetch = (mod.default || mod);
                    return [2 /*return*/, _fetch];
            }
        });
    });
}
function postClick(country) {
    return __awaiter(this, void 0, void 0, function () {
        var fetch, res, j;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, getFetch()];
                case 1:
                    fetch = _a.sent();
                    return [4 /*yield*/, fetch("".concat(BASE, "/click"), {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ country: country }),
                        })];
                case 2:
                    res = _a.sent();
                    return [4 /*yield*/, res.json()];
                case 3:
                    j = _a.sent();
                    return [2 /*return*/, j];
            }
        });
    });
}
function getToday() {
    return __awaiter(this, arguments, void 0, function (limit) {
        var fetch, res;
        if (limit === void 0) { limit = 10; }
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, getFetch()];
                case 1:
                    fetch = _a.sent();
                    return [4 /*yield*/, fetch("".concat(BASE, "/ranks/today?limit=").concat(limit))];
                case 2:
                    res = _a.sent();
                    return [2 /*return*/, res.json()];
            }
        });
    });
}
function getTrending() {
    return __awaiter(this, arguments, void 0, function (limit, decay) {
        var fetch, q, res;
        if (limit === void 0) { limit = 10; }
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, getFetch()];
                case 1:
                    fetch = _a.sent();
                    q = ["limit=".concat(limit)];
                    if (decay !== undefined)
                        q.push("decay=".concat(decay));
                    return [4 /*yield*/, fetch("".concat(BASE, "/ranks/trending?").concat(q.join('&')))];
                case 2:
                    res = _a.sent();
                    return [2 /*return*/, res.json()];
            }
        });
    });
}
function main() {
    return __awaiter(this, void 0, void 0, function () {
        var _a, _b, _c, _d;
        return __generator(this, function (_e) {
            switch (_e.label) {
                case 0:
                    console.log('Posting clicks: KR x3, US x2, JP x1');
                    return [4 /*yield*/, postClick('KR')];
                case 1:
                    _e.sent();
                    return [4 /*yield*/, postClick('KR')];
                case 2:
                    _e.sent();
                    return [4 /*yield*/, postClick('KR')];
                case 3:
                    _e.sent();
                    return [4 /*yield*/, postClick('US')];
                case 4:
                    _e.sent();
                    return [4 /*yield*/, postClick('US')];
                case 5:
                    _e.sent();
                    return [4 /*yield*/, postClick('JP')];
                case 6:
                    _e.sent();
                    console.log('Waiting 1s for writes to propagate...');
                    return [4 /*yield*/, new Promise(function (r) { return setTimeout(r, 1000); })];
                case 7:
                    _e.sent();
                    console.log('Today ranks:');
                    _b = (_a = console).log;
                    return [4 /*yield*/, getToday(10)];
                case 8:
                    _b.apply(_a, [_e.sent()]);
                    console.log('Trending (decay=0.9):');
                    _d = (_c = console).log;
                    return [4 /*yield*/, getTrending(10, 0.9)];
                case 9:
                    _d.apply(_c, [_e.sent()]);
                    return [2 /*return*/];
            }
        });
    });
}
main().catch(function (e) {
    console.error(e);
    process.exit(1);
});
var node_fetch_1 = require("node-fetch");
// Simple simulation script - requires server running on localhost:8000
function run() {
    return __awaiter(this, void 0, void 0, function () {
        var countries, i, country, today, trending;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    countries = ["KR", "US", "JP"];
                    i = 0;
                    _a.label = 1;
                case 1:
                    if (!(i < 10)) return [3 /*break*/, 4];
                    country = countries[i % countries.length];
                    return [4 /*yield*/, (0, node_fetch_1.default)("http://localhost:8000/click", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ country: country }),
                        })];
                case 2:
                    _a.sent();
                    _a.label = 3;
                case 3:
                    i++;
                    return [3 /*break*/, 1];
                case 4: return [4 /*yield*/, (0, node_fetch_1.default)("http://localhost:8000/ranks/today").then(function (r) { return r.json(); })];
                case 5:
                    today = _a.sent();
                    console.log("today", today);
                    return [4 /*yield*/, (0, node_fetch_1.default)("http://localhost:8000/ranks/trending").then(function (r) { return r.json(); })];
                case 6:
                    trending = _a.sent();
                    console.log("trending", trending);
                    return [2 /*return*/];
            }
        });
    });
}
run().catch(function (e) { return console.error(e); });
