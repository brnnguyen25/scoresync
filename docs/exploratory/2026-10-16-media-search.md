# Exploratory session: media search and filters

**Charter:** Explore `GET /v1/media` search and filters **with** unusual and combined
inputs **to discover** inconsistent, surprising, or incorrect results.

**Tester:** Brian (session driven by Claude Code) · **Date:** 2026-10-17 · **Timebox:** 45 minutes · **Build:** 1613e4b

Local stack: `make dev`, MySQL and Redis in Docker, 795 titles (395 game, 200 movie, 200 tv).

## Session log

| Time | What I tried | What happened | Note |
| --- | --- | --- | --- |
| 17:27 | `page_size=1` smoke test | 200, total 795 | Baseline |
| 17:27 | `year_from=2025&year_to=2020` | 200, total 0 | Q1 |
| 17:27 | `year=2020&year_from=2021` | 200, total 0 | Q1 |
| 17:27 | `min_score=100` | 200, total 0 (top score in data is 98.0) | Correct |
| 17:27 | `min_score=100.0001`, `nan`, `inf` | 422 | `nan` error says "must be <= 100": Q6 |
| 17:27 | `q=%25%25` (`%%`) | total **795**, every title | **B1** |
| 17:27 | `q=__` | total **794**, every title except `W` | **B1** |
| 17:27 | `q=a`, `q=W` | 422, min length 2 | The title `W` can't be found by search at all: Q7 |
| 17:27 | `q=O'Brien`, `q=Pokémon`, `q=Pokemon` | total 0 | No such titles in the data; nothing learned |
| 17:27 | `q=%20%20` (two spaces), `q=%5C%5C` (`\\`) | total 0 | Passes `min_length` but matches nothing; harmless |
| 17:28 | `q=Leon`, `q=LEON`, `q=léon` | All find *Léon: The Professional* | Accent- and case-insensitive (MySQL collation). Good |
| 17:28 | `q=appetit`, `q=shippuden`, `q=merli` | Each finds its accented title | Good |
| 17:28 | `q=Thief's` (straight `'`) | total **0**; title is *A Thief’s End* (curly `’`) | **B3** |
| 17:28 | `q=Baldur’s` (curly) | total 0; titles use straight `'` | **B3**, the reverse case |
| 17:28 | `q=Wall-E` | total 0; title is `WALL·E` | Same family as B3; Q8 |
| 17:28 | `q=1998` | 3 games whose titles end in `(1998)` | Data: year suffixes in titles, Q9 |
| 17:28 | `q=given` | `given` (tv) and `Given` (movie) | Same title across media is legitimate, but the tv title is lower-case: Q9 |
| 17:28 | `genre=rpg` / `RPG` / `Rpg` | 98 each | Case-insensitive. Good |
| 17:28 | `genre=action%20%26%20adventure` | 74 | Correct when encoded |
| 17:28 | `genre=action%20&%20adventure` (raw `&`) | 200, total 0, no error | Splits into `genre=action ` plus a stray param: Q3 |
| 17:28 | `genre=%20rpg` | total 0 | Not trimmed: Q3 |
| 17:28 | `genre=action&genre=rpg` | 98 (rpg only) | Last value silently wins: Q2 |
| 17:28 | `genre=nonexistent` | 200, total 0 | Q3 |
| 17:28 | `page=40&page_size=20` / `page=41` | 15 items, then empty with total 795 | Correct |
| 17:28 | `page=0`, `10001`, `abc`; `page_size=0`, `-1`, `101` | 422 each | Correct |
| 17:28 | `page_size=100` | 200 | Correct |
| 17:28 | Walked every sort at `page_size=100`, and movies at `page_size=7` | 795/795 and 200/200 unique ids, no gaps | `Media.id` tiebreaker works |
| 17:28 | `sort=score` with missing scores | Not testable: no title has a null score | Code puts nulls last for `score` and `year`: A4 |
| 17:28 | `sort=title` | `¿Quieres…` and `“The Shorts”…` come before `12 Angry Men` | Q5 |
| 17:28 | `sort=-title`, `medium=GAME`, `medium=book` | 422 | Strict enums. Fine |
| 17:28 | Same query twice | MISS, then HIT | Good |
| 17:28 | Same params in a different order | MISS, a second cache entry | **B2** |
| 17:28 | `min_score=90.0` vs `90`; explicit `page=1`; `genre=RPG` vs `rpg` | MISS each, identical data | **B2** |
| 17:28 | 5 requests with `junk=<random>` | 200 each; Redis keys 262 → 268 | **B2**: unknown params accepted and cached |
| 17:28 | `redis-cli --scan` | Keys look like `scoresync-cache:scoresync-cache::/v1/media?…` | Prefix doubled: B2, cosmetic |

## Bugs

Drafted with the fields of `.github/ISSUE_TEMPLATE/bug_report.yml`, ready to file.

### B1: `q` treats `%` and `_` as SQL wildcards

- **Steps:** `curl -s "localhost:8000/v1/media?q=%25%25"`, then `curl -s "localhost:8000/v1/media?q=__"`
- **Expected:** Titles that contain a literal `%%` or `__` (none in the data, so total 0).
- **Actual:** `%%` returns total 795, every title. `__` returns 794, every title that is at least 2 characters long.
- **Severity:** S3 – minor, workaround exists
- **Found by:** exploratory session
- **Environment:** local, 1613e4b
- **Evidence:** [app/api/routes/media.py](../../app/api/routes/media.py) builds `Media.title.ilike(f"%{q}%")` without escaping. The fix is `Media.title.contains(q, autoescape=True)` or an explicit `escape=`.

### B2: Cache key is the raw query string

- **Steps:**
  1. `curl -si "localhost:8000/v1/media?medium=game&min_score=90" | grep -i x-fastapi-cache` twice gives MISS, then HIT.
  2. `curl -si "localhost:8000/v1/media?min_score=90&medium=game" | grep -i x-fastapi-cache` gives MISS.
  3. `?medium=game&min_score=90.0` and `?medium=game&min_score=90&page=1` also give MISS.
  4. `?junk=<random>` five times adds 5 Redis keys.
- **Expected:** Requests that mean the same thing share one cache entry, and unknown parameters don't create new ones.
- **Actual:** `url_key_builder` uses `request.url.query` verbatim. The same data is cached once per spelling, and any client can add unlimited keys (and skip the cache) by appending a junk parameter. Key names also repeat the prefix (`scoresync-cache:scoresync-cache::`), because the decorator already passes `prefix` in `namespace`.
- **Severity:** S3 – minor, workaround exists. Rate limiting caps the damage, and keys expire after 300 s.
- **Found by:** exploratory session
- **Environment:** local, 1613e4b
- **Evidence:** [app/core/cache.py](../../app/core/cache.py) line 12. A fix is to build the key from the validated endpoint kwargs (sorted) instead of the URL.

### B3: A straight apostrophe doesn't match a curly one in titles

- **Steps:** `curl -s "localhost:8000/v1/media?q=Thief's"`
- **Expected:** *Uncharted 4: A Thief’s End*. People type `'`, not `’`.
- **Actual:** total 0. The reverse fails too: `q=Baldur’s` finds none of the four *Baldur's* titles.
- **Severity:** S3 – minor, workaround exists
- **Found by:** exploratory session
- **Environment:** local, 1613e4b
- **Evidence:** Titles in the data mix `'` and `’` (*Bowser’s Fury* vs *Bowser's Inside Story*). Fix in one place: normalize punctuation at ingest (`app/normalize`) and on `q`, or store a normalized search column.

## Questions

1. **Contradictory filters:** `year_from > year_to`, or `year` outside `year_from`/`year_to`, returns 200 with an empty list. Should it return 422 so the client learns the request makes no sense?
2. **Repeated `genre`:** `genre=action&genre=rpg` silently uses the last value. Should this be multi-genre (AND or OR), or a 422?
3. **Unknown genre:** `genre=nonexistent`, `genre=%20rpg` (leading space), and a raw `&` that splits `action & adventure` all return 200 with total 0. Should we trim whitespace, and should an unknown genre return 422 listing the valid genres? There are only 41.
4. **Unknown query params** (`junk=1`) are accepted silently. Is that intended? It is what makes the B2 cache flooding possible.
5. **Title sort:** this is a plain collation order, so `¿Quieres ser mi hijo?` and `“The Shorts”…` sort before `12 Angry Men`. Should a sort key skip leading punctuation?
6. **`min_score=nan`** gets 422 "Input should be less than or equal to 100". Correct to reject it, but the message is misleading.
7. **`q` min length 2** means the game `W` can never be found by search. Acceptable?
8. **`Wall-E` vs `WALL·E`:** should search fold punctuation in general (`·`, `–`, `’`), or is B3 enough?
9. **Data:** game titles carry source suffixes such as `Soulcalibur (1998)`, `LittleBigPlanet (PS Vita)` and `Mirror's Edge (Mobile)`. The TV title `given` is lower-case. *The Legend of Zelda: Collector's Edition* (a compilation) ranks #3 overall at 95.0. Strip the suffixes at ingest? Should compilations be excluded?

## Ideas for automation

- **A1:** `q` with `%`, `_` and `\` matches only literally (guards B1).
- **A2:** Reordered parameters and equivalent values hit the same cache key, and an unknown parameter adds no key (guards B2).
- **A3:** `q=Thief's` finds a title stored with `’`, and vice versa (guards B3).
- **A4:** A fixture with null `aggregate_score` and null `release_year` checks that nulls sort last for `score`, `-score`, `year` and `-year`. The live data has no nulls, so this path is untested today.
- **A5:** Walk every page under each sort and assert unique ids and count == total. It passes now; keep it as a regression guard.
- **A6:** `genre` is case-insensitive, and encoded `action & adventure` matches.
- **A7:** Data-quality checks (`app/quality`): flag title suffixes like `(YYYY)` or `(Platform)`, mixed apostrophe styles, and titles that differ only by case.

## Debrief

I covered every area in the charter: contradictory filters, special characters in `q`, genre names, pagination edges, sorting, the data itself, and caching. I couldn't test where null scores sort, because the current data has none; A4 covers that with a fixture instead. The session found **3 bugs** (LIKE wildcards in `q`, a cache key built from the raw query string, apostrophe mismatch) and raised **9 questions**, mostly about whether a request that makes no sense should return 200-empty or 422. Pagination and input validation held up well. What surprised me: accented search already works through MySQL collation (`Leon` finds `Léon`), yet a plain apostrophe breaks search because the source data mixes `'` and `’`.

**Next charters**

- After deploy: explore rate limiting **with** forged client-IP headers (`X-Forwarded-For`, `X-Real-IP`) **to discover** whether the limit can be bypassed. This ties into B2: junk params plus a rate-limit bypass would mean unbounded cache growth.
- Explore `GET /v1/media/{id}` and `/history` **with** titles that have many sources or snapshots **to discover** wrong "latest score" selection.
