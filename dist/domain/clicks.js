import { ddbDocClient } from "../aws/ddb.js";
import { UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { dayKey, minuteKey } from "./time.js";
const TABLE_TODAY = process.env.CLICKS_TODAY_TABLE || "ClicksToday";
const TABLE_MINUTE = process.env.CLICKS_MINUTE_TABLE || "ClicksMinute";
export async function recordClick(country) {
    const now = new Date().toISOString();
    const day = dayKey();
    const minute = minuteKey();
    const ttl = Math.floor(Date.now() / 1000) + 20 * 60; // +20 minutes
    // Update ClicksToday
    const p1 = ddbDocClient.send(new UpdateCommand({
        TableName: TABLE_TODAY,
        Key: { scope: `day#${day}`, country },
        UpdateExpression: "ADD #c :inc SET updatedAt = :u",
        ExpressionAttributeNames: { "#c": "count" },
        ExpressionAttributeValues: { ":inc": 1, ":u": now },
    }));
    // Update ClicksMinute
    const p2 = ddbDocClient.send(new UpdateCommand({
        TableName: TABLE_MINUTE,
        Key: { minute, country },
        UpdateExpression: "ADD #c :inc SET #ttl = :ttl",
        ExpressionAttributeNames: { "#c": "count", "#ttl": "ttl" },
        ExpressionAttributeValues: { ":inc": 1, ":ttl": ttl },
    }));
    // Basic retry: try both, but don't require transaction
    try {
        await Promise.all([p1, p2]);
        return { ok: true };
    }
    catch (err) {
        // simple retry once
        try {
            await Promise.all([p1, p2]);
            return { ok: true };
        }
        catch (err2) {
            throw err2;
        }
    }
}
