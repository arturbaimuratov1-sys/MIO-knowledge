"""Reassemble split LFS assets after `git lfs pull` (Python standard library)."""
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def restore(root):
    manifest = json.loads((root / 'models-lfs-manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['split_files']:
        target = root / entry['path']
        if target.exists():
            if target.stat().st_size == entry['size'] and digest(target) == entry['sha256']:
                print(f'Already verified: {entry["path"]}')
                continue
            raise RuntimeError(f'Existing file differs; move it aside first: {target}')
        parts = [root / part for part in entry['parts']]
        for part in parts:
            if not part.is_file():
                raise RuntimeError(f'Missing {part}; run git lfs pull first')
            with part.open('rb') as stream:
                if stream.read(128).startswith(b'version https://git-lfs.github.com/spec/v1'):
                    raise RuntimeError(f'LFS pointer found in {part}; run git lfs pull first')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.assembling')
        h = hashlib.sha256()
        size = 0
        created = False
        try:
            with temporary.open('xb') as output:
                created = True
                for part in parts:
                    with part.open('rb') as stream:
                        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                            output.write(block)
                            h.update(block)
                            size += len(block)
            if size != entry['size'] or h.hexdigest() != entry['sha256']:
                raise RuntimeError(f'Checksum/size mismatch: {entry["path"]}')
            temporary.rename(target)
        except BaseException:
            if created and temporary.exists():
                temporary.unlink()
            raise
        print(f'Restored and verified: {entry["path"]}')


if __name__ == '__main__':
    restore(Path(__file__).resolve().parents[1])
