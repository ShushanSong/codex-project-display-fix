#!/usr/bin/env python3
"""Restore Codex desktop project records, including required rootPaths. MIT."""
import argparse
from contextlib import closing
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime


def desktop_running():
    if os.name != 'nt':
        raise RuntimeError('Apply is supported on Windows only; preview works elsewhere.')
    command = "@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { ($_.Name -ieq 'ChatGPT.exe' -and $_.ExecutablePath -match 'OpenAI\\.Codex') -or $_.Name -ieq 'Codex.exe' }).Count"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or not result.stdout.strip().isdigit():
        raise RuntimeError('Cannot verify Codex process state; no changes written.')
    return int(result.stdout.strip()) > 0


def recover(home, apply=False, check_running=desktop_running):
    home = Path(home).expanduser().resolve()
    if apply and check_running():
        raise RuntimeError('Codex is running. Exit it fully before applying.')
    state_path = home / '.codex-global-state.json'
    db_path = home / 'state_5.sqlite'
    if not state_path.is_file() or not db_path.is_file():
        raise RuntimeError('Missing global state or state_5.sqlite.')
    before = state_path.read_bytes()
    state = json.loads(before.decode('utf-8'))
    if not isinstance(state, dict):
        raise RuntimeError('Global state must be a JSON object.')
    with closing(sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Database integrity check failed.')
        rows = conn.execute('SELECT id,name,position,created_at_ms,updated_at_ms FROM projects ORDER BY position').fetchall()
        roots = conn.execute('SELECT project_id,path FROM project_roots ORDER BY position').fetchall()
    if not rows:
        raise RuntimeError('Database contains no projects; this recovery does not apply.')
    recovered = {}
    missing = 0
    for row in rows:
        paths = [root['path'] for root in roots if root['project_id'] == row['id']]
        if not paths or not all(isinstance(p, str) and p for p in paths):
            raise RuntimeError('A database project has no valid root path; review manually.')
        missing += sum(not Path(p).is_dir() for p in paths)
        recovered[row['id']] = {'id':row['id'], 'name':row['name'], 'rootPaths':paths, 'createdAt':row['created_at_ms'], 'updatedAt':row['updated_at_ms']}
    current = state.get('local-projects', {})
    order = state.get('project-order', [])
    if not isinstance(current, dict) or not isinstance(order, list) or not all(isinstance(i, str) for i in order):
        raise RuntimeError('Unsupported existing project configuration; review manually.')
    updated = copy.deepcopy(state)
    # Preserve additional metadata (for example ChatGPT backing), and valid roots.
    for key, item in recovered.items():
        existing = current.get(key)
        if isinstance(existing, dict):
            merged = {**item, **existing}
            paths = merged.get('rootPaths')
            if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p for p in paths):
                merged['rootPaths'] = item['rootPaths']
            recovered[key] = merged
    updated['local-projects'] = {**current, **recovered}
    updated['project-order'] = list(dict.fromkeys([*order, *recovered]))
    changed = sorted(k for k in updated.keys() | state.keys() if updated.get(k) != state.get(k))
    if not set(changed) <= {'local-projects', 'project-order'}:
        raise RuntimeError('Unexpected configuration change.')
    report = {'mode':'apply' if apply else 'preview', 'projects':len(recovered), 'missing_root_folders':missing, 'changed_keys':changed, 'database_changed':False}
    if apply and changed:
        if check_running():
            raise RuntimeError('Codex is running; no changes written.')
        if state_path.read_bytes() != before:
            raise RuntimeError('Configuration changed during preview; retry after closing Codex.')
        backup = home / 'backups' / ('project-rootpaths-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        shutil.copy2(state_path, backup / state_path.name)
        fd, name = tempfile.mkstemp(prefix='.project-rootpaths-', suffix='.tmp', dir=home)
        tmp = Path(name)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
                json.dump(updated, handle, ensure_ascii=False, indent=2)
                handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
            if json.loads(tmp.read_text(encoding='utf-8')) != updated:
                raise RuntimeError('Temporary configuration verification failed.')
            if state_path.read_bytes() != before or check_running():
                raise RuntimeError('Codex restarted or state changed; no changes written.')
            os.replace(tmp, state_path)
        finally:
            tmp.unlink(missing_ok=True)
        if json.loads(state_path.read_text(encoding='utf-8')) != updated:
            raise RuntimeError('Written configuration verification failed; inspect backup.')
        report['backup'] = str(backup)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))))
    parser.add_argument('--apply', action='store_true', help='Back up and write project display configuration; close Codex first.')
    args = parser.parse_args()
    try:
        print(json.dumps(recover(args.codex_home, args.apply), ensure_ascii=True, indent=2))
    except (RuntimeError, OSError, ValueError, sqlite3.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()

