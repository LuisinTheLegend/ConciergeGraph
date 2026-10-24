import sys

pkgs = [
    'tree_sitter',
    'tree_sitter_python',
    'tree_sitter_javascript',
    'tree_sitter_typescript',
    'tree_sitter_go',
    'tree_sitter_rust',
]

print("Python version:", sys.version)
print("=" * 60)
for pkg in pkgs:
    try:
        mod = __import__(pkg)
        ver = getattr(mod, '__version__', 'unknown')
        print(f"{pkg:25}: INSTALLED (version: {ver})")
    except ImportError as e:
        print(f"{pkg:25}: NOT INSTALLED ({e})")
