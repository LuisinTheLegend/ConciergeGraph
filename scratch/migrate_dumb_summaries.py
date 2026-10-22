"""scratch/migrate_dumb_summaries.py

Script da Rodada 4.1/H: Migracao dos sumarios [DUMB] para NULL.
Suporta --dry-run (padrao) e --apply.
Realiza backup via API conn.backup(), valida integridade, aplica em transacao unica,
verifica contagens, valida checksum das colunas preservadas e integridade do FTS5.
"""

import argparse
import datetime
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT_DIR / "data/concierge.db"
DEFAULT_BACKUP_DIR = ROOT_DIR / "data/backups"

def compute_content_checksum(conn: sqlite3.Connection) -> str:
    """Calcula checksum deterministico de (id, label, content, type, node_type, tags, file_hash, status)."""
    cur = conn.cursor()
    query = """
        SELECT id, label, content, type, node_type, tags, file_hash, status
        FROM nodes
        ORDER BY id ASC;
    """
    hasher = hashlib.sha256()
    for row in cur.execute(query):
        row_str = "|".join("" if v is None else str(v) for v in row)
        hasher.update(row_str.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()

def get_node_counts(conn: sqlite3.Connection) -> dict:
    """Retorna contagens detalhadas da tabela nodes."""
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
    dumb = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary LIKE '[DUMB]%';").fetchone()[0]
    nulls = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NULL;").fetchone()[0]
    others = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NOT NULL AND summary NOT LIKE '[DUMB]%';").fetchone()[0]
    return {
        "total": total,
        "dumb": dumb,
        "nulls": nulls,
        "others": others,
    }

def perform_sqlite_backup(src_conn: sqlite3.Connection, backup_dir: Path) -> Path:
    """Cria backup consistente usando a API sqlite3 backup."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"concierge_{timestamp}.db"
    
    print(f"Criando backup via sqlite3 backup API: {backup_file} ...")
    bck_conn = sqlite3.connect(str(backup_file))
    src_conn.backup(bck_conn, pages=250)
    bck_conn.close()
    
    # Validacao do backup
    val_conn = sqlite3.connect(str(backup_file))
    val_cur = val_conn.cursor()
    integrity = val_cur.execute("PRAGMA integrity_check;").fetchall()
    if not integrity or integrity[0][0] != "ok":
        val_conn.close()
        raise RuntimeError(f"FALHA: Backup {backup_file} corrompido: {integrity}")
    
    val_counts = get_node_counts(val_conn)
    val_conn.close()
    
    print(f"Backup validado com sucesso (integrity_check: ok, contagens: {val_counts}).")
    return backup_file

def run_migration(db_path: Path, backup_dir: Path, apply_changes: bool):
    print("=" * 70)
    print("MIGRACAO DOS SUMARIOS [DUMB] PARA NULL (RODADA 4.1/H)")
    print(f"Modo: {'APPLY (Gravacao no banco)' if apply_changes else 'DRY-RUN (Simulacao segura)'}")
    print(f"Banco alvo: {db_path}")
    print("=" * 70)

    if not db_path.exists():
        raise FileNotFoundError(f"Banco de dados nao encontrado: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.isolation_level = None  # Gerenciamento explicito de transacao

    # 1. Checagem inicial
    counts_before = get_node_counts(conn)
    checksum_before = compute_content_checksum(conn)
    print("\n[ESTADO INICIAL]")
    print(f"  Total de nos:          {counts_before['total']}")
    print(f"  Nos com [DUMB]%:       {counts_before['dumb']}")
    print(f"  Nos com summary NULL:  {counts_before['nulls']}")
    print(f"  Nos com outro resumo:  {counts_before['others']}")
    print(f"  Checksum preservado:   {checksum_before}")

    if counts_before["dumb"] == 0:
        print("\nNenhum sumario [DUMB] encontrado para migrar. Encerrando.")
        conn.close()
        return

    # 2. Backup se for modo apply
    backup_file = None
    if apply_changes:
        backup_file = perform_sqlite_backup(conn, backup_dir)

    # 3. Execucao da Migracao em Transacao Unica
    cur = conn.cursor()
    expected_updates = counts_before["dumb"]

    print(f"\nIniciando transacao: UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%' ...")
    cur.execute("BEGIN TRANSACTION;")
    try:
        cur.execute("UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%';")
        affected_rows = cur.rowcount
        print(f"Linhas afetadas reportadas: {affected_rows} (esperado: {expected_updates})")

        if affected_rows != expected_updates:
            cur.execute("ROLLBACK;")
            raise RuntimeError(
                f"ABORTADO: Numero de linhas afetadas ({affected_rows}) difere do esperado ({expected_updates}). Rollback executado."
            )

        if apply_changes:
            cur.execute("COMMIT;")
            print("Transacao EFETIVADA (COMMIT) com sucesso.")
        else:
            cur.execute("ROLLBACK;")
            print("DRY-RUN: Transacao REVERTIDA (ROLLBACK) com sucesso. Nenhuma mudanca gravada.")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"ERRO durante UPDATE: {e}. Rollback executado.")
        conn.close()
        raise

    # 4. Validacoes Pos-Migracao
    # Se estavamos em dry-run, reconectamos para inspecionar o estado que permaneceu
    # Se apply_changes foi True, avaliamos o estado persistido
    counts_after = get_node_counts(conn)
    checksum_after = compute_content_checksum(conn)

    print("\n[ESTADO POS-OPERACAO]")
    print(f"  Total de nos:          {counts_after['total']}")
    print(f"  Nos com [DUMB]%:       {counts_after['dumb']}")
    print(f"  Nos com summary NULL:  {counts_after['nulls']}")
    print(f"  Nos com outro resumo:  {counts_after['others']}")
    print(f"  Checksum preservado:   {checksum_after}")

    checksum_ok = (checksum_before == checksum_after)
    print(f"  Validacao de Checksum: {'IDENTICO (Sucesso - colunas preservadas intocadas)' if checksum_ok else 'DIVERGENTE (Falha)'}")
    if not checksum_ok:
        conn.close()
        raise RuntimeError("ERRO CRITICO: Checksum do conteudo divergiu apos a operacao!")

    # 5. Verificacoes de Integridade do FTS5
    print("\n[VERIFICACAO FTS5]")
    try:
        # FTS5 integrity-check
        cur.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
        print("  FTS5 integrity-check: OK (sem erros)")
    except Exception as fts_err:
        print(f"  FTS5 integrity-check: FALHA ({fts_err})")
        conn.close()
        raise

    summary_fts_matches = cur.execute("SELECT COUNT(*) FROM nodes_fts WHERE nodes_fts MATCH 'summary: DUMB';").fetchone()[0]
    global_fts_matches = cur.execute("SELECT COUNT(*) FROM nodes_fts WHERE nodes_fts MATCH 'DUMB';").fetchone()[0]

    if apply_changes:
        print(f"  FTS5 MATCH 'summary: DUMB': {summary_fts_matches} resultados encontrados")
        print(f"  FTS5 MATCH global 'DUMB':   {global_fts_matches} resultados encontrados")
        if global_fts_matches > 0:
            labels_matching = cur.execute("SELECT rowid, label FROM nodes_fts WHERE nodes_fts MATCH 'DUMB' LIMIT 5;").fetchall()
            for r_id, r_lbl in labels_matching:
                clean_lbl = str(r_lbl).encode("ascii", "replace").decode("ascii")
                print(f"    - Match legitimo no campo label: id={r_id}, label='{clean_lbl}'")

        if summary_fts_matches > 0:
            conn.close()
            raise RuntimeError(f"ERRO: FTS5 ainda contem {summary_fts_matches} matches em 'summary: DUMB' apos aplicacao!")
    else:
        print(f"  DRY-RUN: FTS5 mantem estado original devido ao ROLLBACK ({global_fts_matches} matches globais).")

    conn.close()
    print("\n" + "=" * 70)
    print("OPERACAO CONCLUIDA COM SUCESSO.")
    if backup_file:
        print(f"Backup de seguranca disponivel em: {backup_file}")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migracao de sumarios [DUMB] para NULL no Grafo Concierge")
    parser.add_argument("--apply", action="store_true", help="Aplica as alteracoes permanentemente (padrao: False, apenas dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Modo simulacao segura (padrao)")
    parser.add_argument("--db-path", default=str(DEFAULT_DB), help="Caminho do banco SQLite")
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Diretorio para gravacao do backup")

    args = parser.parse_args()
    apply_mode = args.apply and not args.dry_run

    run_migration(
        db_path=Path(args.db_path),
        backup_dir=Path(args.backup_dir),
        apply_changes=apply_mode,
    )
