#!/usr/bin/env python3
"""hf_upload.py — upload a reference image to Higgsfield and record its UUID under a NAME:
receipts/<NAME>-upload-id.txt (what hf_submit.py and the refs gate resolve). Uploads are free and persist;
one name per reference, the name is what appears in the gate table and the GO ask.

  hf_upload.py --root <project> <image.png> [--name NAME]      (NAME defaults to the file stem)
"""
import argparse, json, os, subprocess, sys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image')
    ap.add_argument('--root', default='.')
    ap.add_argument('--name')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    name = a.name or os.path.splitext(os.path.basename(a.image))[0]
    dest = os.path.join(root, 'receipts', f'{name}-upload-id.txt')
    if os.path.exists(dest):
        print(f'{name}: already uploaded → {open(dest).read().strip()} ({dest})'); return
    out = subprocess.run(['higgsfield', 'upload', 'create', a.image, '--json'], capture_output=True, text=True)
    os.makedirs(os.path.join(root, 'receipts', 'raw'), exist_ok=True)
    open(os.path.join(root, 'receipts', 'raw', f'upload-{name}.json'), 'w', encoding='utf-8').write(out.stdout + '\n--stderr--\n' + out.stderr)
    try:
        j = json.loads(out.stdout)
    except Exception:
        sys.exit(f'{name}: UNPARSED reply — {out.stdout[:200]} {out.stderr[:200]}')
    top = j[0] if isinstance(j, list) and j else j
    uid = (top.get('id') or top.get('upload_id') or top.get('uuid')) if isinstance(top, dict) else (top if isinstance(top, str) else None)
    if not uid:
        sys.exit(f'{name}: no id in reply — {json.dumps(j)[:300]}')
    open(dest, 'w').write(str(uid).strip() + '\n')
    print(f'{name} → {uid}  ({os.path.relpath(dest, root)})')


if __name__ == '__main__':
    main()
