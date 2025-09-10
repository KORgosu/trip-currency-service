import { DateTime } from "luxon";
// All KST (Asia/Seoul)
export function nowKst() {
    return DateTime.now().setZone("Asia/Seoul");
}
export function dayKey(dt = nowKst()) {
    return dt.toFormat("yyyyLLdd"); // YYYYMMDD
}
export function minuteKey(dt = nowKst()) {
    return dt.toFormat("yyyyLLddHHmm"); // YYYYMMDDHHmm
}
export function minuteKeysRange(now = nowKst(), spanMinutes = 15) {
    const keys = [];
    for (let i = 0; i < spanMinutes; i++) {
        const dt = now.minus({ minutes: i });
        keys.push(dt.toFormat("yyyyLLddHHmm"));
    }
    return keys;
}
