const BASE = process.env.BASE_URL || 'http://localhost:8000';
let _fetch = null;
async function getFetch() {
    if (_fetch)
        return _fetch;
    // dynamic import to avoid TS duplicate type issues in some environments
    const mod = await import('node-fetch');
    _fetch = (mod.default || mod);
    return _fetch;
}
async function postClick(country) {
    const fetch = await getFetch();
    const res = await fetch(`${BASE}/click`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ country }),
    });
    const j = await res.json();
    return j;
}
async function getToday(limit = 10) {
    const fetch = await getFetch();
    const res = await fetch(`${BASE}/ranks/today?limit=${limit}`);
    return res.json();
}
async function getTrending(limit = 10, decay) {
    const fetch = await getFetch();
    const q = [`limit=${limit}`];
    if (decay !== undefined)
        q.push(`decay=${decay}`);
    const res = await fetch(`${BASE}/ranks/trending?${q.join('&')}`);
    return res.json();
}
async function main() {
    console.log('Posting clicks: KR x3, US x2, JP x1');
    await postClick('KR');
    await postClick('KR');
    await postClick('KR');
    await postClick('US');
    await postClick('US');
    await postClick('JP');
    console.log('Waiting 1s for writes to propagate...');
    await new Promise((r) => setTimeout(r, 1000));
    console.log('Today ranks:');
    console.log(await getToday(10));
    console.log('Trending (decay=0.9):');
    console.log(await getTrending(10, 0.9));
}
main().catch((e) => {
    console.error(e);
    process.exit(1);
});
import fetch from "node-fetch";
// Simple simulation script - requires server running on localhost:8000
async function run() {
    const countries = ["KR", "US", "JP"];
    for (let i = 0; i < 10; i++) {
        const country = countries[i % countries.length];
        await fetch("http://localhost:8000/click", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ country }),
        });
    }
    const today = await fetch("http://localhost:8000/ranks/today").then((r) => r.json());
    console.log("today", today);
    const trending = await fetch("http://localhost:8000/ranks/trending").then((r) => r.json());
    console.log("trending", trending);
}
run().catch((e) => console.error(e));
