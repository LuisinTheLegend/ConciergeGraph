import os
import sys
import tempfile
import logging
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

def check():
    print("=== BEFORE BOOTSTRAP ===")
    root_logger = logging.getLogger()
    print("Root handlers count:", len(root_logger.handlers))
    for idx, h in enumerate(root_logger.handlers):
        print(f"  [{idx}] {h.__class__.__module__}.{h.__class__.__name__} (id={hex(id(h))})")

    # Set temporary paths to avoid touching real data
    temp_dir = tempfile.mkdtemp()
    temp_db = os.path.join(temp_dir, "test.db")
    temp_chroma = os.path.join(temp_dir, "chroma")
    os.environ["GRAFO_DB_PATH"] = temp_db
    os.environ["GRAFO_CHROMA_PATH"] = temp_chroma
    os.environ["GRAFO_JANITOR_INTERVAL"] = "99999"

    import main
    main.DB_PATH = temp_db
    main.CHROMA_PATH = temp_chroma
    main.setup_logging("INFO")

    print("\n=== AFTER setup_logging ===")
    print("Root handlers count:", len(root_logger.handlers))
    for idx, h in enumerate(root_logger.handlers):
        print(f"  [{idx}] {h.__class__.__module__}.{h.__class__.__name__} (id={hex(id(h))})")

    server, janitor, store = main.bootstrap()

    print("\n=== AFTER bootstrap ===")
    print("Root handlers count:", len(root_logger.handlers))
    for idx, h in enumerate(root_logger.handlers):
        print(f"  [{idx}] {h.__class__.__module__}.{h.__class__.__name__} (id={hex(id(h))})")

    store.close()

    import mcp
    import rich
    print(f"\nmcp version: {getattr(mcp, '__version__', 'unknown')}")
    print(f"rich version: {getattr(rich, '__version__', 'unknown')}")

    # Inspect fastmcp source / handlers installation
    import mcp.server.fastmcp as fastmcp_mod
    print(f"fastmcp file: {fastmcp_mod.__file__}")

if __name__ == "__main__":
    check()
