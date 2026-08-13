# Load Testing — ForensiX ZR Unit

## How to run

```bash
cd forensix_backend_python
pip install -r load_tests/requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000   # in one terminal

# in another terminal
locust -f load_tests/locustfile.py --host http://127.0.0.1:8000 \
  --headless -u 50 -r 5 -t 60s --csv=load_tests/results
```

`load_tests/locustfile.py` simulates two kinds of users:
- **ReadHeavyOfficer** — logs in, then repeatedly hits dashboard/reports/cases listing endpoints (not rate-limited). Measures real server/DB throughput.
- **WritingCitizen** — registers and repeatedly submits reports (rate-limited). Demonstrates behavior under the current per-IP rate limits.

## Results (50 concurrent users, 60s run, local machine, SQLite)

| Endpoint | Median | 95th %ile | Notes |
|---|---|---|---|
| `GET /api/dashboard/stats` | 8ms | 19ms | Fast — DB/server not the bottleneck |
| `GET /api/reports/` | 7ms | 16ms | Fast |
| `GET /api/cases/` | 7ms | 18ms | Fast |
| `POST /api/reports/` (create) | 9ms | 30ms | Fast when authenticated |
| `POST /api/auth/login` | 33ms | 72ms (then floods of 429s) | Rate-limit bottleneck, not DB |
| `POST /api/auth/register` | 54ms | mostly 429s | Rate-limit bottleneck |

**Raw server/DB throughput is not the bottleneck** — every read/write endpoint responds in single-digit-to-low-double-digit milliseconds even under concurrent load. The bottleneck found is entirely in authentication.

## Findings

### 1. Fixed (found and patched during this test): unhandled 500 on duplicate officer code
`POST /api/auth/register` crashed with an unhandled `sqlite3.IntegrityError` / 500 Internal Server Error when two requests tried to register with the same `officer_code` (which is a unique-per-user column). Fixed in `app/routes/auth.py`: the code is now checked for availability before insert, and the `db.commit()` is wrapped so any remaining race condition returns a clean `400` instead of crashing.

### 2. Rate limiting is per-IP, not per-user (design tradeoff, not a bug — but worth knowing)
`slowapi`'s `get_remote_address` key function limits by source IP. In this load test, every simulated user shares the test machine's IP, so the whole swarm exhausts the shared `5/minute` register and `10/minute` login budget almost immediately — every user past the first few in that window gets `429`, and every downstream authenticated request they make then fails with `401` (no token).

This is realistic for any real-world scenario where many genuine users share one public IP (office network, campus Wi-Fi, mobile carrier NAT). **Recommendation, not yet implemented:** consider a higher shared-IP allowance, or layering a per-account limit in addition to per-IP (e.g. `slowapi` supports composite keys), before a public launch where many citizens might report from the same network.

## Conclusion

The application server and database layer (tested against SQLite, the local-dev default) handle concurrent read/write traffic well — response times stay low even at 50 concurrent simulated users. The practical scaling question for this app is **authentication rate-limit tuning**, not raw server capacity. PostgreSQL (already supported via `DATABASE_URL`) is still recommended over SQLite for real production traffic, since SQLite serializes all writes — this test didn't run long/hard enough to hit that ceiling, but it will show up under sustained write-heavy load (e.g. many simultaneous evidence uploads).
