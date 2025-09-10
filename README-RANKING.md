# Country Ranking Service (DynamoDB-only)

This folder implements a simple Country Click Ranking backend that stores all data in DynamoDB.

Key points
- Storage: DynamoDB only (ClicksToday, ClicksMinute)
- Server: Node.js + TypeScript + Fastify
- Timezone: Asia/Seoul (KST) used for day/minute keys
- In-memory cache: 5-10s (configurable via `CACHE_TTL_SECONDS`)

Quick start (local)
1. Install dependencies:

```powershell
npm install
npm run build
```

2. (Optional) Create DynamoDB tables in AWS:

```bash
bash scripts/create-dynamodb-tables.sh
```

3. Start server:

```powershell
# from repo root
node dist/server.js
```

4. Run simulation (posts clicks and reads ranks):

```powershell
# requires node-fetch installed (it is a dependency)
node --loader ts-node/esm scripts/simulate.ts
# or use ts-node if configured: npm run sim
```

Env vars
- AWS_REGION (default ap-northeast-2)
- CLICKS_TODAY_TABLE (default ClicksToday)
- CLICKS_MINUTE_TABLE (default ClicksMinute)
- CACHE_TTL_SECONDS (default 10)
- DEFAULT_DECAY (default 0.9)

Notes
- Click writes update both ClicksToday and ClicksMinute via UpdateItem ADD operations.
- ClicksMinute TTL should be enabled to avoid unbounded storage growth (script attempts to enable it).
- This service is intentionally simple: no Redis, no Lambda. It favors operational simplicity and observability.# Country Click Ranking Service (DynamoDB-only)

Goal: implement country click ranking using DynamoDB only (no Lambda, no Redis).

Quick start

1. Install deps

```powershell
npm install
```

2. Create DynamoDB tables (or use provided script)

```powershell
# requires AWS CLI configured
bash scripts/create-dynamodb-tables.sh
# enable TTL for ClicksMinute using attribute 'ttl'
```

3. Run in dev

```powershell
npm run dev
```

APIs

- POST /click { country: "KR" }
- GET  /ranks/today?limit=50
- GET  /ranks/trending?limit=50&decay=0.9

Notes

- Timezone: Asia/Seoul (KST)
- Cache: in-memory short TTL (default 10s)
- Data model: ClicksToday (PK scope day#YYYYMMDD, SK country), ClicksMinute (PK minute YYYYMMDDHHmm, SK country)
- No Lambda/Redis used.

Testing

- Use `npm run sim` to run a small simulation that posts clicks and fetches ranks (requires server running)

Operational notes

- For high QPS, increase cache TTL to 30s or shard trending queries into coarser buckets to reduce DynamoDB read cost.

