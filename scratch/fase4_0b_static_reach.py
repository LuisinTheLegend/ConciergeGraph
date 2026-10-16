import os
import ast
from collections import defaultdict, deque

def find_project_files():
    files_map = {}
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in (
            '.git', '.agents', '.github', '.mypy_cache', '.pytest_cache', 
            '__pycache__', 'tests', 'scratch', 'audits', 'grafo-dashboard-web', 
            'data', 'docs-grafo-concierge'
        ) and not d.startswith('_test')]
        for f in files:
            if f.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, f), '.').replace('\\', '/')
                files_map[rel_path] = f
    return files_map

def file_to_module(rel_path):
    if rel_path == 'main.py':
        return 'main'
    clean = rel_path.removesuffix('.py')
    if clean.endswith('/__init__'):
        clean = clean.removesuffix('/__init__')
    return clean.replace('/', '.')

def get_module_package(rel_path):
    # Determines the __package__ of the file
    dir_path = os.path.dirname(rel_path).replace('\\', '/')
    if not dir_path or dir_path == '.':
        return ''
    return dir_path.replace('/', '.')

def get_parent_packages(mod_name):
    parts = mod_name.split('.')
    parents = []
    for i in range(1, len(parts)):
        parents.append('.'.join(parts[:i]))
    return parents

def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def extract_imports(filepath, rel_path, all_modules):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            tree = ast.parse(f.read(), filename=filepath)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return set()

    current_pkg = get_module_package(rel_path)
    imported_mods = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_name = alias.name
                # check if mod_name or any prefix is in all_modules
                if mod_name in all_modules:
                    imported_mods.add(mod_name)
                else:
                    # check if prefix is a project module
                    parts = mod_name.split('.')
                    for i in range(len(parts)-1, 0, -1):
                        prefix = '.'.join(parts[:i])
                        if prefix in all_modules:
                            imported_mods.add(prefix)
                            break
        elif isinstance(node, ast.ImportFrom):
            level = node.level
            mod_str = node.module or ''
            
            if level == 0:
                base_pkg = mod_str
            else:
                # relative import
                pkg_parts = current_pkg.split('.') if current_pkg else []
                # level 1 means current package
                # level 2 means parent of current package, etc.
                if level - 1 > len(pkg_parts):
                    # Relative import beyond top-level
                    base_pkg = ''
                else:
                    target_parts = pkg_parts[:len(pkg_parts) - (level - 1)]
                    if mod_str:
                        base_pkg = '.'.join(target_parts + [mod_str]) if target_parts else mod_str
                    else:
                        base_pkg = '.'.join(target_parts)

            # Check if base_pkg itself is a module
            if base_pkg in all_modules:
                imported_mods.add(base_pkg)

            # Also check if each alias is a submodule of base_pkg
            for alias in node.names:
                candidate = f"{base_pkg}.{alias.name}" if base_pkg else alias.name
                if candidate in all_modules:
                    imported_mods.add(candidate)

    # For every imported module, also include its parent packages
    final_imports = set()
    for m in imported_mods:
        final_imports.add(m)
        for p in get_parent_packages(m):
            if p in all_modules:
                final_imports.add(p)

    return final_imports

def main():
    files_map = find_project_files()
    file_by_mod = {file_to_module(p): p for p in files_map}
    mod_by_file = {p: file_to_module(p) for p in files_map}
    all_modules = set(file_by_mod.keys())

    # Build graph
    imports_by_mod = {}
    imported_by = defaultdict(set)
    for p, mod in mod_by_file.items():
        imps = extract_imports(p, p, all_modules)
        # remove self-import if any
        imps.discard(mod)
        imports_by_mod[mod] = imps
        for imp in imps:
            imported_by[imp].add(mod)

    # Reachability from 'main'
    reachable = set()
    queue = deque(['main'])
    reachable.add('main')

    while queue:
        curr = queue.popleft()
        for nxt in imports_by_mod.get(curr, []):
            if nxt not in reachable:
                reachable.add(nxt)
                queue.append(nxt)

    unreachable = all_modules - reachable

    # Group unreachable by package
    by_pkg = defaultdict(list)
    total_unreachable_lines = 0
    for mod in unreachable:
        filepath = file_by_mod[mod]
        lines = count_lines(filepath)
        total_unreachable_lines += lines
        parts = mod.split('.')
        pkg = parts[0] if len(parts) > 1 else 'root'
        by_pkg[pkg].append((mod, filepath, lines))

    print("=" * 80)
    print("GRAFO ESTATICO DE ALCANCE A PARTIR DE main.py")
    print("=" * 80)
    print(f"Total de modulos do projeto: {len(all_modules)}")
    print(f"Total de modulos alcancaveis: {len(reachable)}")
    print(f"Total de modulos NAO alcancaveis: {len(unreachable)}")
    print(f"Total de linhas em modulos NAO alcancaveis: {total_unreachable_lines}")
    print()

    print("MODULOS NAO ALCANCAVEIS POR PACOTE:")
    for pkg in sorted(by_pkg.keys()):
        print(f"\n--- Pacote: {pkg} ({len(by_pkg[pkg])} modulos) ---")
        for mod, filepath, lines in sorted(by_pkg[pkg], key=lambda x: x[1]):
            print(f"  - {filepath} ({lines} linhas) [modulo: {mod}]")

    print("\n" + "=" * 80)
    print("QUEM IMPORTA CADA MODULO NAO ALCANCAVEL (E SE O IMPORTADOR E INALCANCAVEL):")
    print("=" * 80)
    for mod in sorted(unreachable):
        filepath = file_by_mod[mod]
        importers = imported_by.get(mod, set())
        if not importers:
            print(f"[{mod}] ({filepath}):")
            print("    -> NINGUEM importa em producao (orfao absoluto)")
        else:
            print(f"[{mod}] ({filepath}):")
            for imp in sorted(importers):
                imp_file = file_by_mod.get(imp, imp)
                is_imp_unreachable = imp in unreachable
                status = "TAMBEM INALCANCAVEL" if is_imp_unreachable else "ALCANCAVEL (atencao!)"
                print(f"    <- Importado por: {imp} ({imp_file}) [{status}]")

    print("\n" + "=" * 80)
    print("MODULOS ALCANCAVEIS (TOTAL: {})".format(len(reachable)))
    print("=" * 80)
    for mod in sorted(reachable):
        filepath = file_by_mod[mod]
        lines = count_lines(filepath)
        print(f"  + {filepath} ({lines} linhas) [modulo: {mod}]")

if __name__ == '__main__':
    main()
