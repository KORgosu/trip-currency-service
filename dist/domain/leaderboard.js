import { ddbDocClient } from "../aws/ddb.js";
import { QueryCommand } from "@aws-sdk/lib-dynamodb";
import { minuteKeysRange, dayKey } from "./time.js";
const TABLE_TODAY = process.env.CLICKS_TODAY_TABLE || "ClicksToday";
const TABLE_MINUTE = process.env.CLICKS_MINUTE_TABLE || "ClicksMinute";
// default to 0 in development so clicks are reflected immediately; override via env for production
const CACHE_TTL = Number(process.env.CACHE_TTL_SECONDS || "0");
const DEFAULT_DECAY = Number(process.env.DEFAULT_DECAY || "0.9");
// simple in-memory cache
const cache = new Map();
function getCached(key) {
    const v = cache.get(key);
    if (!v)
        return null;
    if (Date.now() > v.exp) {
        cache.delete(key);
        return null;
    }
    return v.data;
}
function setCached(key, data, ttl = CACHE_TTL) {
    cache.set(key, { exp: Date.now() + ttl * 1000, data });
}
export async function getTodayRanks(limit = 50) {
    const day = dayKey();
    const cacheKey = `today:${day}:${limit}`;
    const cached = getCached(cacheKey);
    if (cached)
        return cached;
    const params = {
        TableName: TABLE_TODAY,
        KeyConditionExpression: "#scope = :s",
        ExpressionAttributeNames: { "#scope": "scope" },
        ExpressionAttributeValues: { ":s": `day#${day}` },
    };
    const resp = await ddbDocClient.send(new QueryCommand(params));
    const items = resp.Items || [];
    const ranks = items
        .map((i) => ({ country: i.country, count: Number(i.count || 0) }))
        .sort((a, b) => b.count - a.count)
        .slice(0, limit);
    setCached(cacheKey, ranks);
    return ranks;
}
export async function getTrending(limit = 50, decay = DEFAULT_DECAY) {
    const now = undefined; // placeholder for keys
    const keys = minuteKeysRange(undefined, 15);
    const cacheKey = `trending:${keys[0]}:${limit}:${decay}`;
    const cached = getCached(cacheKey);
    if (cached)
        return cached;
    // query in parallel
    const queries = keys.map((k) => ddbDocClient.send(new QueryCommand({
        TableName: TABLE_MINUTE,
        KeyConditionExpression: "#minute = :m",
        ExpressionAttributeNames: { "#minute": "minute" },
        ExpressionAttributeValues: { ":m": k },
    })));
    const results = await Promise.all(queries);
    const agg = {};
    results.forEach((r, idx) => {
        const items = (r.Items || []);
        const t = idx; // 0 = now, 1 = now-1, ...
        items.forEach((it) => {
            const c = it.country;
            const count = Number(it.count || 0);
            const weight = Math.pow(decay, t);
            agg[c] = (agg[c] || 0) + count * weight;
        });
    });
    const ranks = Object.entries(agg)
        .map(([country, score]) => ({ country, score }))
        .sort((a, b) => b.score - a.score)
        .slice(0, limit);
    setCached(cacheKey, ranks);
    return ranks;
}
