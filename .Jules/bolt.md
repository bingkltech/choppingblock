## 2024-04-14 - Replace batch execute calls with executemany
**Learning:** SQLite backend operations over individual connections inside a loop can be performance bottlenecks, especially during the initialization phase or startup sequence.
**Action:** Replace looped `execute` statements with `executemany` over arrays of values to reduce DB roundtrips.
