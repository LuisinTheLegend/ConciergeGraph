import sqlite3
import time

def demonstrate_collision():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    
    # Create projects table
    cur.execute("""
    CREATE TABLE projects (
        uuid TEXT PRIMARY KEY,
        folder_name TEXT NOT NULL
    );
    """)
    
    # Create files table as currently defined in tests and architecture
    cur.execute("""
    CREATE TABLE files (
        path TEXT PRIMARY KEY,
        content TEXT,
        ssh_hash TEXT,
        body_hash TEXT,
        is_dirty INTEGER DEFAULT 1,
        community_id TEXT,
        last_modified REAL
    );
    """)
    
    cur.execute("INSERT INTO projects (uuid, folder_name) VALUES ('proj-alpha-111', 'alpha_repo');")
    cur.execute("INSERT INTO projects (uuid, folder_name) VALUES ('proj-beta-222', 'beta_repo');")
    
    # Both projects have 'src/utils.py'
    rel_path = "src/utils.py"
    
    # Project 1 inserts its file via DeltaManager logic
    print("--- 1. Projeto Alpha insere 'src/utils.py' ---")
    cur.execute(
        "INSERT INTO files (path, content, ssh_hash, body_hash, is_dirty, community_id) VALUES (?, ?, ?, ?, 1, ?);",
        (rel_path, "def alpha_fn(): pass", "ssh_alpha", "lbh_alpha", "community_alpha")
    )
    print("Alpha inserido com sucesso. Linhas na tabela files:")
    for r in cur.execute("SELECT path, content, community_id FROM files;"):
        print(" ", r)
        
    # Project 2 tries to insert its file with same relative path
    print("\n--- 2. Projeto Beta tenta inserir 'src/utils.py' ---")
    try:
        cur.execute(
            "INSERT INTO files (path, content, ssh_hash, body_hash, is_dirty, community_id) VALUES (?, ?, ?, ?, 1, ?);",
            (rel_path, "def beta_fn(): pass", "ssh_beta", "lbh_beta", "community_beta")
        )
        print("Beta inserido com sucesso (inesperado).")
    except sqlite3.IntegrityError as e:
        print(f"COLISAO DETECTADA (IntegrityError): {e}")
        
    print("\n--- 3. E se usar INSERT OR REPLACE (ou ON CONFLICT)? ---")
    cur.execute(
        "INSERT OR REPLACE INTO files (path, content, ssh_hash, body_hash, is_dirty, community_id) VALUES (?, ?, ?, ?, 1, ?);",
        (rel_path, "def beta_fn(): pass", "ssh_beta", "lbh_beta", "community_beta")
    )
    print("Resultado apos INSERT OR REPLACE:")
    for r in cur.execute("SELECT path, content, community_id FROM files;"):
        print(" ", r)
    print("SOBREESCRITA SILENCIOSA: O arquivo do Projeto Beta apagou os dados do Projeto Alpha!")

if __name__ == "__main__":
    demonstrate_collision()
