#!/usr/bin/env python3
"""refs_gate.py — the REFS GATE. No generation call (a video seed, an image-model still) is submitted
without every locked reference in THIS call's reference set — checked in code, before the GO, never from
memory. In reference-driven generation the references ARE the product: a correctly named, correctly uploaded
reference showing the wrong person, garment or room passes a name check and burns the whole batch — so the gate
opens the file, not just the name.

Layout under --root (default: the current directory):
  prompts/refs-required.json     the rules — see references/refs-required.example.json in the skill
  receipts/refs-gate.jsonl       the ledger: PASS records, registrations, imports, acceptances, keeper-crop derivations
  receipts/<NAME>-upload-id.txt  a reference uploaded for target `hf`
  refs-urls.json                 references uploaded for target `kie` ({NAME: url})
  monid-urls.json                references hosted on sfs for target `monid` ({NAME: url} + `_meta`;
                                 monid_upload.py). For this target the gate ALSO checks the signed url's
                                 expiry — a lapsed url FAILS, because the model fetches it at generation
                                 time and the job bills at acceptance. The fix is a free re-issue.
  treg-urls.json                 references hosted on treg for target `treg` ({NAME: url} + `_meta`;
                                 treg_host.py). Same expiry check, one fact different: a `treg host`
                                 url is an OPAQUE token with a 7-day TTL and NOTHING encoded in it, so
                                 an unrecorded expiry cannot be recovered from the url the way monid's
                                 `?e=` recovers it — it FAILS rather than warns. Re-hosting is free and
                                 mints a NEW url, so the ledger is rewritten, never patched.

Rules: each rule = an element (a regex over the prompt body, negated clauses removed) + the reference ROLES it needs;
a role is met by any listed reference NAME that is in --refs AND uploaded for --target, or inherited from the START
IMAGE's own accepted record. A start image with no record FAILS; one not --accept'ed FAILS; one whose lineage reaches
neither a KEEPER take nor a CLIENT-SUPPLIED import FAILS unless --fresh-scene is declared. Every capitalised subject in
the prompt without a rule FAILS as UNRULED unless declared --births (born in this gen) or --prose (prose-only on purpose).
CONTENT: every cited reference's file is re-hashed against its registration (a changed file FAILS), decoded, and sized
(a short side under min_side FAILS). An unregistered or unaccepted reference is a WARN — a FAIL when the rules set
require_ref_files / require_ref_acceptance. The gate proves the file is the one that was ACCEPTED; what it shows is the
acceptance note's job (a detector that fails confidently is worse than none).
LOOK: when the rules list look_plates, light or grade language in the prose with no look plate cited FAILS (--prose LOOK
keeps a prose-only light on purpose). COMPETING: a cited reference no matched rule depends on is a WARN — a reference
the prompt does not need competes with the ones it does.

  refs_gate.py --prompt <file> --refs A,B,C [--target hf|kie|monid|treg] [--start-image NAME] [--births R,R]
               [--prose X,Y] [--fresh-scene] [--record NAME]            → table + REFS-GATE PASS|FAIL, exit 0|1
  refs_gate.py --register NAME --file <path>                            → bind a reference name to its file (sha256, size)
  refs_gate.py --import NAME --file <path> --provenance "<who, when, how>" → a CLIENT-SUPPLIED asset, a lineage root of its own
  refs_gate.py --record NAME --derived-from SRC [--adds ROLE,ROLE] [--file <path>]  → ledger record for a keeper crop
  refs_gate.py --accept NAME --note "<the rows zoom-checked, the role named>" [--file <path>] → a reference may feed a gen after this
  refs_gate.py --selftest
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, time

# One upload ledger per target. `hf` has none: it writes receipts/<NAME>-upload-id.txt per reference.
LEDGERS = {'kie': 'refs-urls.json', 'monid': 'monid-urls.json', 'treg': 'treg-urls.json',
           'hfapi': 'hf-api-urls.json'}
# Targets whose reference url LAPSES, so the gate reads its expiry before the GO. The value is
# whether an unrecorded expiry can be resolved WITHOUT paying for it: monid signs with `?e=<unix>`
# so the url answers the question itself; the Higgsfield API signs its upload `x-amz-tagging:
# retention=temporary` and states no window at all, but a HEAD on the public url is free, so the
# unknown converts to a fact at zero cost. treg has neither — an opaque token and no free probe — so
# there an unrecorded expiry FAILS. No free route to the answer ⇒ FAIL; a free route ⇒ WARN naming it.
EXPIRING = {'monid': True, 'treg': False, 'hfapi': True}
REFRESH = {'monid': 'monid_upload.py', 'treg': 'treg_host.py',
           'hfapi': 'hf_api_upload.py'}                         # the free fix, named in the FAIL row

CAPS = re.compile(r'\b[A-Z][A-Z0-9]{1,}\b')
DEFAULT_TAKE_RE = r'^S\d\d-[A-Z0-9]+(-v\d+)?-s\d+$'   # a generated take id — a root that continues a scene
DEFAULT_SPOT_RE = r'(S\d\d)'
DEFAULT_LOOK = (r'\b(?:day ?light|sun ?light|lamp ?light|lighting|golden hour|blue hour|dusk|dawn|tungsten|fluorescent|overcast|'
                r'backlit|back-lit|(?:warm|cool|soft|hard|practical) (?:light|warmth)|palette|colou?r grade|exposure|moonlight)\b')
VIDEO_EXT = ('.mp4', '.mov', '.webm', '.mkv', '.m4v')


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def media_dims(p):
    """(width, height) of an image or a video, or None when it does not decode"""
    if p.lower().endswith(VIDEO_EXT):
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', p], capture_output=True, text=True)
        try:
            w, h = (int(x) for x in r.stdout.strip().split(',')[:2]); return w, h
        except Exception:
            return None
    try:
        from PIL import Image
        with Image.open(p) as im:
            im.load(); return im.size
    except Exception:
        return None


class Gate:
    def __init__(self, root, rules_path=None, ledger_path=None):
        self.root = os.path.abspath(root)
        self.rules_path = rules_path or os.path.join(self.root, 'prompts', 'refs-required.json')
        self.ledger = ledger_path or os.path.join(self.root, 'receipts', 'refs-gate.jsonl')
        r = json.load(open(self.rules_path, encoding='utf-8'))
        self.rules = r['rules']
        self.stop = set(r.get('caps_stoplist', []))
        self.embeds = r.get('embeds', {})
        self.take_re = re.compile(r.get('take_regex', DEFAULT_TAKE_RE))
        self.spot_re = re.compile(r.get('spot_regex', DEFAULT_SPOT_RE))
        self.require_files = bool(r.get('require_ref_files', False))
        self.require_accept = bool(r.get('require_ref_acceptance', False))
        self.look_plates = r.get('look_plates')              # None = the look gate is off, and a WARN row says so
        self.look_re = re.compile(r.get('look_language', DEFAULT_LOOK), re.I)
        self.min_side = int(r.get('min_side', 256))

    # --- storage -------------------------------------------------------------------------------
    def uploaded(self, name, target):
        if target == 'hf':
            return os.path.exists(os.path.join(self.root, 'receipts', f'{name}-upload-id.txt'))
        # monid hosts its references on sfs (free, and a lapsed URL is re-issued rather than re-uploaded);
        # treg hosts them on treg.to (free, but the BYTES die with the url — a refresh re-uploads);
        # kie uploads to its own store, where a lapsed URL means a real re-upload. One ledger each.
        p = os.path.join(self.root, LEDGERS.get(target, 'refs-urls.json'))
        return os.path.exists(p) and name in json.load(open(p, encoding='utf-8'))

    def url_freshness(self, name, label, target):
        """A monid or treg reference rides as a url that LAPSES. The name being present in the ledger
        proves nothing about the url still resolving, and the model fetches it at generation time — so a
        lapsed url would pass a name check and fail (or worse, silently drop a reference) after the job is
        already billed at acceptance. Expiry is read LOCALLY, at zero API calls: from the recorded
        expiry, else from the url itself where the url carries one. Both fixes are free, so this fails closed.

        The two targets differ in exactly one place, and it is the reason EXPIRING is a map and not a set:
        monid signs its url with `?e=<unix>`, so a lost ledger is recoverable and an unrecorded expiry is
        only a WARN; `treg host` mints an opaque token that encodes nothing, so an unrecorded expiry
        cannot be recovered at all and FAILS."""
        led = LEDGERS.get(target)
        p = os.path.join(self.root, led)
        if not os.path.exists(p):
            return [], 0
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            return [(f'{label} url', 'WARN', f'{led} does not parse')], 0
        url = d.get(name)
        if not isinstance(url, str):
            return [], 0
        meta = (d.get('_meta') or {}).get(name) or {}
        exp = meta.get('expiresAt') or meta.get('expires_at')      # monid spells it one way, treg the other
        left = None
        if exp:
            for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z'):   # isoformat() drops .%f at a whole second
                try:
                    t = time.strptime(exp.replace('Z', '+0000'), fmt)
                    left = time.mktime(t) - time.timezone - time.time()
                    break
                except Exception:
                    continue
        if left is None and EXPIRING.get(target):
            m = re.search(r'[?&]e=(\d+)', url)
            if m:
                left = int(m.group(1)) - time.time()
        if left is None:
            if EXPIRING.get(target):
                return [(f'{label} url', 'WARN',
                         f'no expiry recorded — free check: {REFRESH[target]} --root <project> --verify')], 0
            return [(f'{label} url', 'FAIL',
                     'no expiry recorded, and a `treg host` url is an opaque token that carries none — '
                     f'nothing local can say whether it still resolves. Free fix: treg_host.py --root <project> '
                     f'--refresh {name} --go')], 1
        if left <= 0:
            return [(f'{label} url', 'FAIL',
                     f'the {target} reference url has EXPIRED — the model fetches it at generation time, and the '
                     f'job bills at acceptance. Free fix: {REFRESH[target]} --root <project> --refresh {name} --go')], 1
        if left < 1800:
            return [(f'{label} url', 'WARN',
                     f'url lapses in {left/60:.0f} min and a generation p95 is ~10 min — '
                     f'refresh it before the GO (free)')], 0
        return [(f'{label} url', 'ok', f'{target} url good for {left/3600:.1f} h')], 0

    def latest_record(self, asset):
        rec = None
        if os.path.exists(self.ledger):
            for line in open(self.ledger, encoding='utf-8'):
                line = line.strip()
                if line:
                    j = json.loads(line)
                    if j.get('asset') == asset:
                        rec = j
        return rec

    def append(self, j):
        os.makedirs(os.path.dirname(self.ledger), exist_ok=True)
        with open(self.ledger, 'a', encoding='utf-8') as f:
            f.write(json.dumps(j) + '\n')
        return j

    def file_facts(self, path):
        ap = path if os.path.isabs(path) else os.path.join(self.root, path)
        if not os.path.exists(ap): sys.exit(f'REFS-GATE: no file at {path}')
        dims = media_dims(ap)
        if not dims: sys.exit(f'REFS-GATE: {path} does not decode as an image or a video')
        return {'file': os.path.relpath(ap, self.root), 'sha256': sha256(ap), 'bytes': os.path.getsize(ap), 'dims': list(dims)}

    # --- lineage --------------------------------------------------------------------------------
    def lineage(self, asset, seen=None):
        """Walk an asset's record back through derived_from / refs to a KEEPER take or a CLIENT-SUPPLIED import. A chain
        that ends at a sheet or a text-to-image still is NOT rooted — that start image would start a NEW world."""
        seen = set(seen or ())
        if asset in seen:
            return [asset], False
        seen.add(asset)
        if self.take_re.match(asset):
            return [asset], True
        rec = self.latest_record(asset)
        if rec is None:
            return [asset], False
        if rec.get('client_supplied'):
            return [f"{asset} (client-supplied: {rec.get('provenance', '?')})"], True
        parents = ([rec['derived_from']] if rec.get('derived_from') else []) + \
                  [r for r in (rec.get('refs') or []) if r != asset]
        best = None
        for par in parents:
            chain, rooted = self.lineage(par, seen)
            if rooted:
                return [asset] + chain, True
            if best is None:
                best = chain
        return [asset] + (best or []), False

    # --- content --------------------------------------------------------------------------------
    def content(self, name, label):
        """the file behind a reference name: registered, unchanged, decodable, big enough — and accepted"""
        rec = self.latest_record(name)
        if not rec or not rec.get('file'):
            lvl = 'FAIL' if self.require_files else 'WARN'
            return [(f'{label} content', lvl, f'unregistered — the gate cannot see what it shows: refs_gate.py --register {name} --file <path>')], int(lvl == 'FAIL')
        ap = os.path.join(self.root, rec['file'])
        if not os.path.exists(ap):
            return [(f'{label} content', 'FAIL', f"its registered file is missing: {rec['file']}")], 1
        if sha256(ap) != rec.get('sha256'):
            return [(f'{label} content', 'FAIL', f"{rec['file']} CHANGED since it was registered — re-check it, then --register and --accept it again")], 1
        dims = media_dims(ap)
        if not dims:
            return [(f'{label} content', 'FAIL', f"{rec['file']} does not decode")], 1
        if min(dims) < self.min_side:
            return [(f'{label} content', 'FAIL', f"{rec['file']} is {dims[0]}x{dims[1]} — under {self.min_side} px on its short side, too small to carry a reference")], 1
        return [(f'{label} content', 'ok', f"{rec['file']} {dims[0]}x{dims[1]} · sha256 {rec['sha256'][:10]}… unchanged")], 0

    # --- the check --------------------------------------------------------------------------------
    def check(self, prompt_text, refs, target='hf', start_image=None, births=(), prose=(), spot=None, fresh=False):
        births, prose = set(births), set(prose)
        refs = [r for r in refs if r]
        exp = list(refs)
        for r in refs:
            for e in self.embeds.get(r, []):
                if e not in exp:
                    exp.append(e)
        rows, fail, inherited = [], 0, set()
        if start_image:
            rec = self.latest_record(start_image)
            if rec is None:
                rows.append(('START IMAGE ' + start_image, 'FAIL',
                             'no REFS-GATE record — its content is unverified; regenerate it THROUGH the gate, or --import a client-supplied still')); fail += 1
            elif not rec.get('accepted'):
                inherited = set(rec.get('roles_satisfied', []))
                rows.append(('START IMAGE ' + start_image, 'FAIL',
                             f"generated through the gate but NOT ACCEPTED — zoom-check it against the scene's acceptance rows "
                             f"(pieces, lettering, geometry, cast count, anatomy), then: refs_gate.py --accept {start_image} --note '<what was checked>'")); fail += 1
            else:
                inherited = set(rec.get('roles_satisfied', []))
                rows.append(('START IMAGE ' + start_image, 'ok',
                             f"record {rec.get('ts', '?')} ACCEPTED ({rec.get('note', '')}) → roles {', '.join(sorted(inherited)) or '-'}"))
                chain, rooted = self.lineage(start_image)
                arrow = ' ← '.join(chain)
                if rooted:
                    rows.append(('  lineage → keeper', 'ok', arrow))
                elif fresh:
                    rows.append(('  lineage → keeper', 'ok', f'--fresh-scene declared (a NEW world, no predecessor shot): {arrow}'))
                else:
                    rows.append(('  lineage → keeper', 'FAIL',
                                 f'{arrow} — the start image derives from neither a KEEPER take nor a client-supplied import, so this gen starts a NEW world; '
                                 f"derive the plate from the previous shot's LAST keeper frame, --import the client's approved image, or declare --fresh-scene")); fail += 1
            if rec is not None:
                crows, cfail = self.content(start_image, '  start image'); rows += crows; fail += cfail
        if target in EXPIRING and start_image:
            frows, ffail = self.url_freshness(start_image, '  start image', target); rows += frows; fail += ffail
        for r in refs:
            if not self.uploaded(r, target):
                rows.append(('ref ' + r, 'FAIL', f'not uploaded for target {target}')); fail += 1
            elif target in EXPIRING:
                frows, ffail = self.url_freshness(r, 'ref ' + r, target); rows += frows; fail += ffail
            if r == start_image:
                continue
            crows, cfail = self.content(r, 'ref ' + r); rows += crows; fail += cfail
            rec = self.latest_record(r)
            if not (rec and rec.get('accepted')):
                lvl = 'FAIL' if self.require_accept else 'WARN'
                rows.append((f'ref {r} accepted', lvl, f'not accepted — zoom-check it for the role it plays, then --accept {r} --note "<the rows checked>"')); fail += int(lvl == 'FAIL')
        roles_satisfied = set(inherited) | births
        ruled_caps = set()
        for rule in self.rules:
            ruled_caps |= {t.upper() for t in re.findall(r'[A-Za-z][A-Za-z0-9]{1,}',
                                                        re.sub(r'\\[bBwWdDsS]|\(\?<!|\(\?!', ' ', rule['regex']))}
        # negated clauses ("no device in frame", "never a banner") are not elements of the shot
        body = re.sub(r'\b(?:no|never|without|nor|not)\b[^.;,]*', ' ', prompt_text)
        depended = set()
        for rule in self.rules:
            if rule.get('spots') and spot and spot not in rule['spots']:
                continue
            if not re.search(rule['regex'], body):
                continue
            for role, names in rule['roles'].items():
                depended |= set(names)
                tag = f"{rule['element']} → {role}"
                if role in births:
                    rows.append((tag, 'BORN', 'declared born in this gen')); continue
                if role in prose:
                    rows.append((tag, 'PROSE', 'declared prose-only')); continue
                hit = [n for n in names if n in exp and self.uploaded(n, target)]
                if hit:
                    rows.append((tag, 'ok', 'by ' + hit[0])); roles_satisfied.add(role)
                elif role in inherited:
                    rows.append((tag, 'ok', 'inherited from the start image'))
                else:
                    rows.append((tag, 'FAIL', 'needs one of: ' + ' | '.join(names))); fail += 1
        # the look: light described in prose is a look plate's job
        lm = self.look_re.search(body)
        if lm:
            if self.look_plates is None:
                rows.append(('look', 'WARN', f'light or grade language in the prose ("{lm.group(0)}") and no look_plates in the rules — the look gate is off'))
            else:
                hit = [x for x in refs if x in self.look_plates]
                if hit:
                    rows.append(('look', 'ok', f'"{lm.group(0)}" → look plate {hit[0]}')); depended |= set(hit)
                elif 'LOOK' in prose:
                    rows.append(('look', 'PROSE', f'"{lm.group(0)}" — declared prose-only light'))
                else:
                    rows.append(('look', 'FAIL', f'light or grade language in the prose ("{lm.group(0)}") with no look plate cited — cite the plate for this light context under a look-only role, or declare --prose LOOK')); fail += 1
        # competing: a reference nothing in this prompt depends on
        for r in refs:
            if r == start_image or r in depended:
                continue
            if any(r in self.embeds.get(x, []) for x in refs):
                continue
            listed = any(r in names for rule in self.rules for names in rule['roles'].values()) or (self.look_plates and r in self.look_plates)
            rows.append((f'ref {r}', 'WARN', 'COMPETING — nothing in this prompt depends on it; a reference the prompt does not need competes with the ones it does (drop it, or rule what it carries)'
                         if listed else 'UNRULED reference — no rule names it, so nothing checks what it is for'))
        caps = set(CAPS.findall(body)) - self.stop - ruled_caps
        for c in sorted(caps):
            if c in prose:
                rows.append((f'subject {c}', 'PROSE', 'declared prose-only'))
            elif c in births:
                rows.append((f'subject {c}', 'BORN', 'declared born in this gen'))
            else:
                rows.append((f'subject {c}', 'FAIL', f'UNRULED capitalised subject — add a rule + a reference, or declare --prose {c}')); fail += 1
        return fail == 0, rows, sorted(roles_satisfied)

    def record(self, asset, target, prompt_path, refs, births, roles, derived_from=None, file=None):
        j = {'asset': asset, 'target': target, 'prompt': prompt_path, 'refs': list(refs), 'births': sorted(births),
             'roles_satisfied': sorted(roles), 'ts': time.strftime('%Y-%m-%d %H:%M')}
        if derived_from:
            j['derived_from'] = derived_from
        if file:
            j.update(self.file_facts(file))
        return self.append(j)


def fmt(rows):
    w = max(len(r[0]) for r in rows) if rows else 10
    return '\n'.join(f"  {a:<{w}}  {b:<5}  {c}" for a, b, c in rows)


def csv(s):
    return [x for x in (s or '').split(',') if x]


def selftest():
    """Known-answer cases on a scratch project: a clean set passes; light in prose with no look plate FAILS; a reference
    nothing depends on WARNs as COMPETING; a file changed after acceptance FAILS; an undecodable registered file FAILS;
    a client-supplied import roots the lineage of a start image with no keeper."""
    from PIL import Image
    cases = []
    with tempfile.TemporaryDirectory() as d:
        for sub in ('prompts', 'receipts', 'refs'): os.makedirs(os.path.join(d, sub))
        json.dump({'rules': [{'element': 'the visitor', 'regex': r'\b[Tt]he visitor\b', 'roles': {'PERSON': ['VISITOR-ref']}}],
                   'caps_stoplist': [], 'require_ref_files': True, 'require_ref_acceptance': True, 'look_plates': ['LOOK-warm']},
                  open(os.path.join(d, 'prompts', 'refs-required.json'), 'w'))
        for n, size in (('VISITOR-ref', (512, 768)), ('LOOK-warm', (512, 912)), ('SPARE-ref', (512, 512)), ('CLIENT-photo', (768, 1024)), ('BROKEN-ref', (512, 512))):
            Image.new('RGB', size, (120, 90, 60)).save(os.path.join(d, 'refs', f'{n}.png')); open(os.path.join(d, 'receipts', f'{n}-upload-id.txt'), 'w').write('x\n')
        g = Gate(d)
        for n, extra in (('VISITOR-ref', {}), ('LOOK-warm', {}), ('SPARE-ref', {}), ('BROKEN-ref', {}),
                         ('CLIENT-photo', {'client_supplied': True, 'provenance': 'selftest', 'roles_satisfied': ['PERSON']})):
            g.append({'asset': n, **g.file_facts(f'refs/{n}.png'), 'accepted': True, 'note': 'selftest', **extra})
        P = 'The visitor waits in warm lamp light by the door.'
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm']); cases.append(('a clean reference set PASSES', ok))
        ok, rows, _ = g.check(P, ['VISITOR-ref']); cases.append(('light in the prose with no look plate FAILS', not ok and any(r[0] == 'look' and r[1] == 'FAIL' for r in rows)))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm', 'SPARE-ref']); cases.append(('a reference nothing depends on WARNs (COMPETING / UNRULED), still PASSES', ok and any(r[0] == 'ref SPARE-ref' and r[1] == 'WARN' for r in rows)))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], start_image='CLIENT-photo'); cases.append(('a client-supplied start image roots the lineage', ok and any('client-supplied' in r[2] for r in rows)))
        open(os.path.join(d, 'refs', 'BROKEN-ref.png'), 'wb').write(b'not an image')
        rec = g.latest_record('BROKEN-ref'); rec['sha256'] = sha256(os.path.join(d, 'refs', 'BROKEN-ref.png')); g.append(rec)
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm', 'BROKEN-ref']); cases.append(('an undecodable registered file FAILS', not ok and any('does not decode' in r[2] for r in rows)))
        Image.new('RGB', (512, 768), (10, 200, 10)).save(os.path.join(d, 'refs', 'VISITOR-ref.png'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm']); cases.append(('a file changed after acceptance FAILS', not ok and any('CHANGED' in r[2] for r in rows)))
        # --- target monid: the signed url's expiry, read locally from the ledger and the url itself ---
        now = int(time.time())
        mpath = os.path.join(d, 'monid-urls.json')
        Image.new('RGB', (512, 768), (120, 90, 60)).save(os.path.join(d, 'refs', 'VISITOR-ref.png'))
        rec = g.latest_record('VISITOR-ref'); rec['sha256'] = sha256(os.path.join(d, 'refs', 'VISITOR-ref.png')); g.append(rec)
        live = f'https://sfs.monid.ai/BBB?e={now + 7 * 3600}'
        json.dump({'VISITOR-ref': f'https://sfs.monid.ai/AAA?e={now + 7 * 3600}', 'LOOK-warm': live,
                   '_meta': {}}, open(mpath, 'w'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], target='monid')
        cases.append(('monid: a LIVE signed url passes', ok and any(r[1] == 'ok' and 'good for' in r[2] for r in rows)))
        json.dump({'VISITOR-ref': f'https://sfs.monid.ai/AAA?e={now - 60}', 'LOOK-warm': live,
                   '_meta': {}}, open(mpath, 'w'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], target='monid')
        cases.append(('monid: an EXPIRED signed url FAILS before the GO',
                      not ok and any(r[1] == 'FAIL' and 'EXPIRED' in r[2] for r in rows)))
        json.dump({'VISITOR-ref': f'https://sfs.monid.ai/AAA?e={now + 300}', 'LOOK-warm': live,
                   '_meta': {}}, open(mpath, 'w'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], target='monid')
        cases.append(('monid: a url lapsing inside the gen p95 WARNs but still passes',
                      ok and any(r[1] == 'WARN' and 'lapses in' in r[2] for r in rows)))
        # --- target treg: the same expiry contract, minus the url's own fallback ---
        os.remove(mpath)
        tpath = os.path.join(d, 'treg-urls.json')
        iso = lambda secs: time.strftime('%Y-%m-%dT%H:%M:%S.000000Z', time.gmtime(time.time() + secs))
        tregged = lambda a, b: {'VISITOR-ref': 'https://treg.to/m/AAAAAAAAAAAAAAAAAAAAAAAA',
                                'LOOK-warm': 'https://treg.to/m/BBBBBBBBBBBBBBBBBBBBBBBB',
                                '_meta': {'VISITOR-ref': {'expires_at': iso(a)}, 'LOOK-warm': {'expires_at': iso(b)}}}
        json.dump(tregged(6 * 24 * 3600, 6 * 24 * 3600), open(tpath, 'w'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], target='treg')
        cases.append(('treg: a LIVE hosted url passes', ok and any(r[1] == 'ok' and 'treg url good for' in r[2] for r in rows)))
        json.dump(tregged(-60, 6 * 24 * 3600), open(tpath, 'w'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], target='treg')
        cases.append(('treg: an EXPIRED hosted url FAILS before the GO',
                      not ok and any(r[1] == 'FAIL' and 'EXPIRED' in r[2] and 'treg_host.py' in r[2] for r in rows)))
        t = tregged(6 * 24 * 3600, 6 * 24 * 3600); t['_meta']['VISITOR-ref'] = {}
        json.dump(t, open(tpath, 'w'))
        ok, rows, _ = g.check(P, ['VISITOR-ref', 'LOOK-warm'], target='treg')
        cases.append(('treg: an UNRECORDED expiry FAILS (the opaque token carries none to fall back on)',
                      not ok and any(r[1] == 'FAIL' and 'opaque token' in r[2] for r in rows)))
    for name, ok in cases: print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases); print(f"refs_gate selftest {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.', help='project root (default: cwd)')
    ap.add_argument('--rules', help='rules json (default <root>/prompts/refs-required.json)')
    ap.add_argument('--ledger', help='ledger jsonl (default <root>/receipts/refs-gate.jsonl)')
    ap.add_argument('--prompt', help='prompt file to gate')
    ap.add_argument('--refs', default='', help='comma-separated reference NAMES in @Image order')
    ap.add_argument('--target', default='hf', choices=['hf', 'hfapi', 'kie', 'monid', 'treg'])
    ap.add_argument('--start-image')
    ap.add_argument('--births', default='', help='roles born in this gen')
    ap.add_argument('--prose', default='', help='roles/subjects consciously left prose-only (LOOK = a prose-only light)')
    ap.add_argument('--fresh-scene', action='store_true', help='a scene with no predecessor shot')
    ap.add_argument('--spot', help='override the spot id parsed from the prompt filename')
    ap.add_argument('--record', help='record this asset name on PASS (or with --derived-from)')
    ap.add_argument('--derived-from', help='the keeper/asset a crop was cut from')
    ap.add_argument('--adds', default='', help='roles a derived crop adds')
    ap.add_argument('--register', help='bind a reference NAME to its --file (sha256, size, dims)')
    ap.add_argument('--import', dest='import_', help='register a CLIENT-SUPPLIED asset (needs --file and --provenance)')
    ap.add_argument('--file', help='the file behind --register / --import / --record / --accept')
    ap.add_argument('--provenance', help='who supplied an imported asset, when, and how')
    ap.add_argument('--accept', help='mark a recorded reference ACCEPTED')
    ap.add_argument('--note', default='accepted', help='what was zoom-checked (with --accept)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    g = Gate(a.root, a.rules, a.ledger)
    now = time.strftime('%Y-%m-%d %H:%M')

    if a.register or a.import_:
        name = a.register or a.import_
        if not a.file: sys.exit('REFS-GATE: --register / --import need --file <path>')
        if a.import_ and not a.provenance: sys.exit('REFS-GATE: --import needs --provenance "<who supplied it, when, how>"')
        facts = g.file_facts(a.file); prev = g.latest_record(name) or {}
        j = dict(prev); j.update({'asset': name, **facts, 'ts': now})
        if prev.get('sha256') and prev['sha256'] != facts['sha256']:
            j.pop('accepted', None); j['note'] = f"re-registered with new content (was {prev['sha256'][:10]}…) — accept it again"
        if a.import_:
            j.update({'client_supplied': True, 'provenance': a.provenance})
        g.append(j); print(f"REFS-GATE {'IMPORTED (client-supplied)' if a.import_ else 'REGISTERED'} {name} → {facts['file']} {facts['dims'][0]}x{facts['dims'][1]} sha256 {facts['sha256'][:10]}…"); return
    if a.accept:
        rec = g.latest_record(a.accept)
        if rec is None:
            sys.exit(f"REFS-GATE: no record for {a.accept} — it never passed the gate, was never registered, imported or derived; nothing to accept")
        j = dict(rec)
        if a.file:
            facts = g.file_facts(a.file)
            if rec.get('sha256') and rec['sha256'] != facts['sha256']:
                print(f"REFS-GATE: {a.accept} content differs from its registration — accepting the file checked now")
            j.update(facts)
        if g.require_files and not j.get('file'):
            sys.exit(f'REFS-GATE: {a.accept} has no registered file — accept the file you checked: --accept {a.accept} --file <path> --note "…"')
        j.update({'accepted': True, 'note': a.note, 'ts': now})
        g.append(j); print('REFS-GATE ACCEPTED', j['asset'], '—', j['note']); return
    if a.record and a.derived_from:
        src = g.latest_record(a.derived_from)
        if src is None and not g.take_re.match(a.derived_from):
            sys.exit(f"REFS-GATE: no record for {a.derived_from} — it never passed the gate")
        roles = set((src or {}).get('roles_satisfied', [])) | set(csv(a.adds))
        j = g.record(a.record, (src or {}).get('target', a.target), (src or {}).get('prompt', ''), [], [], roles, derived_from=a.derived_from, file=a.file)
        print('REFS-GATE recorded', j['asset'], '← derived from', a.derived_from, 'roles', ', '.join(j['roles_satisfied'])); return
    if not a.prompt:
        ap.print_help(); sys.exit(2)
    text = open(a.prompt, encoding='utf-8').read()
    spot = a.spot
    if not spot:
        m = g.spot_re.search(os.path.basename(a.prompt)); spot = m.group(1) if m else None
    ok, rows, roles = g.check(text, csv(a.refs), a.target, a.start_image, csv(a.births), csv(a.prose), spot, fresh=a.fresh_scene)
    print(f"REFS-GATE {os.path.relpath(a.prompt, g.root)}  refs: {', '.join(csv(a.refs)) or '-'}  start: {a.start_image or '-'}")
    print(fmt(rows))
    nwarn = sum(1 for r in rows if r[1] == 'WARN')
    print(f"REFS-GATE PASS{f' ({nwarn} warning(s) — answer each in the GO ask)' if nwarn else ''}" if ok else f"REFS-GATE FAIL ({sum(1 for r in rows if r[1] == 'FAIL')} missing) — DO NOT SUBMIT")
    if ok and a.record:
        g.record(a.record, a.target, os.path.relpath(a.prompt, g.root), csv(a.refs), csv(a.births), roles)
        print('REFS-GATE recorded', a.record)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
