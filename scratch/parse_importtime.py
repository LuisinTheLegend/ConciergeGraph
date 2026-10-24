"""
scratch/parse_importtime.py — Analisa a saida de 'python -X importtime' e lista os 20 imports com maior tempo CUMULATIVO.
"""

from __future__ import annotations

import sys
from pathlib import Path


def parse_importtime(input_path: str, top_n: int = 20) -> list[tuple[str, int, int]]:
    """Le arquivo gerado por -X importtime e retorna os top N modulos ordenados por tempo cumulativo."""
    modules: list[tuple[str, int, int]] = []

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("import time:"):
                continue
            parts = line[len("import time:"):].split("|")
            if len(parts) >= 3:
                try:
                    self_time = int(parts[0].strip())
                    cum_time = int(parts[1].strip())
                    mod_name = parts[2].strip()
                    modules.append((mod_name, cum_time, self_time))
                except ValueError:
                    continue

    # Ordenar por tempo cumulativo decrescente
    modules.sort(key=lambda x: x[1], reverse=True)

    print("=" * 80)
    print(f"TOP {top_n} IMPORTS COM MAIOR TEMPO CUMULATIVO (-X importtime)")
    print("=" * 80)
    print(f"{'Ranking':<8} | {'Modulo':<45} | {'Cumulativo (ms)':>16} | {'Self (ms)':>10}")
    print("-" * 80)

    seen = set()
    rank = 1
    top_list = []
    for mod_name, cum_time, self_time in modules:
        if mod_name in seen:
            continue
        seen.add(mod_name)
        cum_ms = cum_time / 1000.0
        self_ms = self_time / 1000.0
        print(f"#{rank:<7} | {mod_name:<45} | {cum_ms:>13.2f} ms | {self_ms:>7.2f} ms")
        top_list.append((mod_name, cum_time, self_time))
        rank += 1
        if rank > top_n:
            break
    print("=" * 80)
    return top_list


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python parse_importtime.py <arquivo_importtime_raw.txt> [top_n]")
        sys.exit(1)
    file_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    parse_importtime(file_path, limit)
