"""Перетворює data/attempts.csv (одна подія = один рядок) на data/features.csv
(одна спроба = один рядок, стовпці = ознаки для моделей).

Запуск з кореня проєкту:
    python -m pip install -r requirements.txt
    python features.py
"""

import os
import sys

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "data", "attempts.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "features.csv")

PHRASE_LEN = 6                                             
SKIP_CODES = {"ShiftLeft", "ShiftRight", "Backspace"}     


def get_presses(attempt):
    attempt = attempt.sort_values("event_idx")
    open_downs = {}                
    presses = []
    for row in attempt.itertuples():
        if row.code in SKIP_CODES:
            continue
        if row.type == "down":
            open_downs[row.code] = row.t_ms
        elif row.code in open_downs:
            presses.append((row.code, open_downs.pop(row.code), row.t_ms))
    presses.sort(key=lambda p: p[1])   
    return presses


def stats(values, name):
    s = pd.Series(values)
    return {
        f"{name}_mean": s.mean(),
        f"{name}_median": s.median(),
        f"{name}_std": s.std(),
        f"{name}_cv": s.std() / s.mean(),
    }


def attempt_features(attempt):
    presses = get_presses(attempt)
    if len(presses) != PHRASE_LEN:
        return None  # спроба з виправленнями або збоєм: пропускаємо

    downs = [p[1] for p in presses]
    ups = [p[2] for p in presses]

    dwell = [u - d for d, u in zip(downs, ups)]                                  # 6 значень
    dd = [downs[i + 1] - downs[i] for i in range(PHRASE_LEN - 1)]                # 5 значень
    ud = [downs[i + 1] - ups[i] for i in range(PHRASE_LEN - 1)]                  # 5, може бути < 0
    uu = [ups[i + 1] - ups[i] for i in range(PHRASE_LEN - 1)]                    # 5 значень
    total_ms = ups[-1] - downs[0]

    first = attempt.iloc[0]
    row = {
        "user_id": first["user_id"],
        "session_id": first["session_id"],
        "attempt_id": first["attempt_id"],
        "total_ms": total_ms,
        "speed_cps": PHRASE_LEN / (total_ms / 1000),
        "backspace_count": first["backspace_count"],
        "error_count": first["error_count"],
    }
    for i, v in enumerate(dwell, 1):
        row[f"dwell_{i}"] = v
    for i, v in enumerate(dd, 1):
        row[f"dd_{i}"] = v
    for i, v in enumerate(ud, 1):
        row[f"ud_{i}"] = v
    for i, v in enumerate(uu, 1):
        row[f"uu_{i}"] = v

    row.update(stats(dwell, "dwell"))
    row.update(stats(ud, "ud"))
    return row


def main():
    if not os.path.exists(INPUT_PATH):
        sys.exit(f"Не знайдено файл: {INPUT_PATH}")

    raw = pd.read_csv(INPUT_PATH, encoding="utf-8")
    rows = []
    skipped = 0
    for _, attempt in raw.groupby("attempt_id"):
        result = attempt_features(attempt)
        if result is None:
            skipped += 1
        else:
            rows.append(result)

    features = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    features.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"Усього спроб у файлі: {raw['attempt_id'].nunique()}")
    print(f"Збережено спроб (придатних): {len(features)}, пропущено: {skipped}")
    print(f"Стовпців у {OUTPUT_PATH}: {features.shape[1]}")


if __name__ == "__main__":
    main()
