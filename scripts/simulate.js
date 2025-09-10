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
