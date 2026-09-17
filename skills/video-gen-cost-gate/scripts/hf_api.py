#!/usr/bin/env python3
"""hf_api.py — the Higgsfield REST API lane's shared floor: the WIRE, the COMPUTED cost line, and the
API wallet's only ledger. Imported by hf_api_upload.py / hf_api_submit.py / hf_api_poll.py; usable
alone for a quote, a balance, a load, or the free vendor estimate.

  hf_api.py quote  --model seedance --resolution 720p --duration 8 --seeds 3 [--input-seconds 5]
  hf_api.py balance                                   # the wallet, from the local ledger
  hf_api.py load --usd 115 --credits 1840 [--note ..] # record a purchase
  hf_api.py estimate --endpoint bytedance/seedance-2.5/reference-to-video --body '{...}'
  hf_api.py models [--grep seedance]                  # GET /models, the authoritative catalog

THREE facts make this file necessary rather than convenient — each is a measured trap:

  1. SEEDANCE HAS NO PRICE TO FETCH. `/estimate` returns TWO shapes and the type must be read, never
     assumed: a fixed-price model answers {"credits","usd","discount"}, and every token-metered model
     answers {"type":"description","pricing_description":"<formula>"} with NO NUMBER AT ALL. The docs'
     "use the estimate returned for your authenticated account as the authoritative amount" simply does
     not apply to Seedance 2.5, so the gate carries the formula and computes — or the GO is hand-quoted.

  2. THE WALLET CANNOT BE READ BACK. There is no balance endpoint, and `higgsfield account status`
     reports the FROZEN PLAN wallet (a separate account with a separate wallet), not this one. An
     un-ledgered spend is therefore not "untracked" but LOST: the balance becomes unknowable and the
     cost line's `balance N → M` row goes with it. This ledger is the only copy that exists.

  3. `urllib` IS REFUSED BY CLOUDFLARE — `403 {"error code: 1010"}` on EVERY endpoint, which reads
     exactly like a uniform auth denial against a bad key. `curl` is accepted. Confirm the instrument
     answers for THIS host before reading a refusal as a fact; the discriminator is an UNAUTHENTICATED
     curl to the same URL returning a clean 401, which proves the endpoint live and the key the only
     remaining variable. Everything here goes over curl, with the key handed in on stdin (`curl -K -`)
     so the secret never reaches argv.

Credentials: HF_API_KEY_ID + HF_API_KEY_SECRET in the environment (never on a command line, never in a
receipt). Load them in the same command that needs them: `set -a; . <env-file>; set +a`.
"""
import argparse, json, math, os, subprocess, sys, time

BASE = 'https://api.higgsfield.ai'
LEDGER = os.environ.get('HF_API_LEDGER') or os.path.expanduser('~/.local/state/higgsfield-api/ledger.json')

# ── The formula, verbatim from the vendor's own /estimate description (read 2026-09-18) ─────────────
#   billable video tokens = ceil((input video seconds + generated video seconds) × W × H × 24 fps / 1024)
#   Image and audio references DO NOT COUNT as video input.
FPS = 24
TOK_DIV = 1024

# $ per 1,000 tokens, LIST. The 0.6× tier bills the INPUT seconds too — which is the whole of the
# `gen > 1.5 × in` extend rule: (in+gen)×0.6 beats a fresh gen×1.0 only when gen exceeds 1.5×in.
RATE_PER_KTOK = {'standard': 0.0214, 'video_input': 0.01284}

# `resolution` is 480p or 720p ONLY on this API's Seedance 2.5 — there is NO 1080p, while the (closed)
# CLI plan did 1080p at 9 cr/s. Orientation does not change the product, so one entry serves 9:16 and 16:9.
RASTER = {'480p': (854, 480), '720p': (1280, 720)}

# Per-model discounts are DATED AND EXPIRING, and the two pricing pages strike through DIFFERENT
# baselines (the models page strikes Higgsfield's own list; the compare page strikes FAL's), so a
# discount is only ever quoted against the list price recorded here. A lapsed discount that goes
# unnoticed under-quotes every GO, so quote() always returns the LIST figure beside the net one.
DISCOUNT = {'seedance-2.5': 0.30, 'minimax-h3': 0.45, 'seedance-2.0': 0.15, 'marketing-studio': 0.20}
DISCOUNT_AS_OF = '2026-09-18'

# Fixed per-second models — a price exists, so /estimate is the better source and this is the fallback.
# H3's 2K tier is its only tier here, and it is 45 % under fal's 2K; fal's 768p row is still cheaper at
# the raster the house rule actually uses. The per-reference surcharge starts at the SIXTH image.
FIXED_PER_S = {'minimax-h3': {'usd_per_s_list': 0.13, 'raster': '2K', 'dur': (5, 15),
                              'extra_ref_usd': 0.08, 'free_refs': 5}}

# YOUR wallet's load rate: what you paid divided by the credits you received. Billing is in CREDITS
# (they expire ONE YEAR after they are added) while the rate table above is in USD, so one of the two
# is always derived — this is the derivation, and a settled receipt is what would replace it.
# `hf_api.py load --usd <paid> --credits <received>` records a purchase and RESETS this rate from it,
# so the figure below is only the fallback for a wallet that has never been loaded.
CREDIT_USD = 0.0625

MODEL_ALIAS = {'seedance': 'seedance-2.5', 'seedance-2.5': 'seedance-2.5', 'seedance25': 'seedance-2.5',
               'h3': 'minimax-h3', 'minimax-h3': 'minimax-h3', 'minimax_h3': 'minimax-h3'}

# reference-to-video is BOTH tiers — it bills standard with image/audio refs and 0.6× the moment a
# VIDEO ref rides along. That is decided per CALL, never per endpoint, so it is not in this map.
TIER_BY_ENDPOINT = {'text-to-video': 'standard', 'image-to-video': 'standard',
                    'video-edit': 'video_input', 'video-extend': 'video_input'}


# ── the wire ────────────────────────────────────────────────────────────────────────────────────────
def creds():
    kid = (os.environ.get('HF_API_KEY_ID') or '').strip()
    sec = (os.environ.get('HF_API_KEY_SECRET') or '').strip()
    if not (kid and sec):
        sys.exit('HF_API_KEY_ID / HF_API_KEY_SECRET absent from the environment.\n'
                 '  set -a; . <your env file>; set +a   — never pass a key on a command line.')
    return f'header = "Authorization: Key {kid}:{sec}"\n'


def api(method, url, body=None, timeout=120, headers=(), upload_file=None, auth=True):
    """One curl call. Returns (http_code:str|None, parsed_json_or_text). NEVER urllib — Cloudflare
    refuses it with 403 error code 1010 on every endpoint, which is indistinguishable from a bad key.
    The credential rides in on stdin as a curl config so it never appears in argv or in `ps`."""
    if not url.startswith('http'):
        url = f"{BASE}/{url.lstrip('/')}"
    # `-X HEAD` makes curl wait for a body that never arrives and then time out; `-I` is the HEAD verb.
    verb = ['-I'] if method.upper() == 'HEAD' else ['-X', method]
    args = ['curl', '-sS'] + verb + [url, '-w', '\n%{http_code}', '--max-time', str(timeout)]
    if auth:
        args[1:1] = ['-K', '-']
    for h in headers:
        args += ['-H', h]
    if upload_file is not None:
        # `-T` streams the file and adds Content-Length only. NEVER add a Content-Type of our own here:
        # the presigned PUT signs `content-type;host;x-amz-tagging`, so a later -H Content-Type REPLACES
        # the vendor's signed value and S3 answers 403 SignatureDoesNotMatch — which reads like a bad
        # key and is actually our own header. Measured 2026-09-18.
        args += ['-T', upload_file]
    elif body is not None:
        args += ['-H', 'Content-Type: application/json', '-d', json.dumps(body)]
    p = subprocess.run(args, input=(creds() if auth else ''), capture_output=True, text=True)
    parts = (p.stdout or '').rsplit('\n', 1)
    if len(parts) != 2:
        return None, ((p.stdout or '') + ' ' + (p.stderr or '')).strip()[:400]
    raw, code = parts[0].strip(), parts[1].strip()
    try:
        return code, json.loads(raw)
    except Exception:
        return code, raw[:400]


def concurrency_hit(code, payload):
    """🔴 The concurrency limit returns 400 Bad Request, NOT 429 — with no Retry-After and no
    rate-limit headers. A caller that reads 400 as a malformed body misdiagnoses a queue that would
    have cleared on its own, and a caller that retries a genuinely malformed body loops forever.
    The vendor's own string is the only discriminator."""
    if str(code) != '400':
        return False
    s = json.dumps(payload) if not isinstance(payload, str) else payload
    return 'concurrent request' in s.lower()


# ── the computed cost line ──────────────────────────────────────────────────────────────────────────
def tokens(resolution, gen_s, in_s=0.0):
    """The vendor's formula, exactly: ceil((in + gen) × W × H × fps / 1024)."""
    w, h = RASTER[resolution]
    return math.ceil((float(in_s) + float(gen_s)) * w * h * FPS / TOK_DIV)


def tokens_ceiling(resolution, gen_s, in_s=0.0):
    """The SAME formula with ByteDance's off-by-one-frame correction applied.

    A formula is a vendor CLAIM until a receipt confirms it. On monid the published ByteDance form
    `W × H × fps × seconds ÷ 1024` was measured SHORT BY EXACTLY ONE FRAME — a 4 s clip returns 97
    frames, not 96, because 4.0416667 s = 97/24 — and only a real receipt found it. Higgsfield's
    wording carries no such frame, and its own list price reproduces the no-extra-frame figure to four
    decimals ($0.2057/s at 480p), so the plain form above is the headline. This is the ceiling the GO
    is safe against until a Higgsfield receipt settles which one bills: one extra frame, W×H/1024
    tokens, ≈ 1 % on a 4 s take and ≈ 0.14 % on a 30 s one."""
    w, h = RASTER[resolution]
    n = 0 if (float(in_s) + float(gen_s)) <= 0 else 1
    return math.ceil(((float(in_s) + float(gen_s)) * FPS + n) * w * h / TOK_DIV)


def tier_for(endpoint, has_video_ref=False):
    """standard, or the 0.6× with-video-input tier. reference-to-video is decided by the CALL."""
    leaf = str(endpoint).rstrip('/').rsplit('/', 1)[-1]
    if leaf in TIER_BY_ENDPOINT:
        return TIER_BY_ENDPOINT[leaf]
    return 'video_input' if has_video_ref else 'standard'


def quote(model='seedance-2.5', resolution='480p', gen_s=5, in_s=0.0, seeds=1,
          endpoint='reference-to-video', has_video_ref=False, n_refs=0):
    """Everything the cost line needs, LIST and NET both, per seed and per batch."""
    model = MODEL_ALIAS.get(str(model).lower(), str(model).lower())
    disc = DISCOUNT.get(model, 0.0)
    q = {'model': model, 'resolution': resolution, 'gen_s': gen_s, 'in_s': float(in_s),
         'seeds': seeds, 'discount': disc, 'discount_as_of': DISCOUNT_AS_OF}

    surcharge = 0.0
    if model in FIXED_PER_S:
        f = FIXED_PER_S[model]
        # The per-reference surcharge is recorded AS CHARGED, beside the already-discounted per-second
        # rate — so it is added AFTER the discount, never scaled by it. Discounting an as-charged fee
        # would under-quote the batch, and under-quoting is the one direction a cost gate may not err in.
        surcharge = max(0, int(n_refs) - f['free_refs']) * f['extra_ref_usd']
        each_list = f['usd_per_s_list'] * float(gen_s)
        q.update({'metered': False, 'raster': f['raster'], 'extra_ref_usd': surcharge,
                  'note': 'fixed per-second — /estimate returns a NUMBER for this one; prefer it'})
    else:
        tier = tier_for(endpoint, has_video_ref)
        tok = tokens(resolution, gen_s, in_s)
        ceil_tok = tokens_ceiling(resolution, gen_s, in_s)
        rate = RATE_PER_KTOK[tier]
        each_list = tok * rate / 1000.0
        w, h = RASTER[resolution]
        q.update({'metered': True, 'tier': tier, 'tokens': tok, 'tokens_ceiling': ceil_tok,
                  'usd_ceiling_each_list': round(ceil_tok * rate / 1000.0, 6),
                  'rate_per_ktok': rate, 'px': w * h, 'frames': round((float(in_s) + gen_s) * FPS)})

    each_net = each_list * (1.0 - disc) + surcharge
    each_list += surcharge
    q.update({'usd_each_list': round(each_list, 6), 'usd_each': round(each_net, 6),
              'usd_total_list': round(each_list * seeds, 6), 'usd_total': round(each_net * seeds, 6),
              'usd_per_s': round(each_net / gen_s, 6) if gen_s else None,
              'credits_total': round(each_net * seeds / CREDIT_USD, 3)})
    return q


def cost_line(q, balance=None):
    """The GO's cost line. Shows the NET as the expected figure and the LIST beside it, because the
    discount is dated and expiring and a lapsed one would silently under-quote every future batch."""
    L = []
    if q['metered']:
        head = (f"{q['seeds']} × {q['gen_s']} s" + (f" (+{q['in_s']:g} s input, BILLED)" if q['in_s'] else '')
                + f" × {q['resolution']} = {q['tokens']:,} tok × ${q['rate_per_ktok']}/1K [{q['tier']}]")
    else:
        head = f"{q['seeds']} × {q['gen_s']} s × {q['raster']}" + (
            f" + ${q['extra_ref_usd']:.2f} refs past 5" if q.get('extra_ref_usd') else '')
    L.append(f"cost: {head} = ${q['usd_each']:.4f} each → ${q['usd_total']:.4f}"
             f"  ({q['credits_total']:.1f} cr @ ${CREDIT_USD}/cr"
             + (f", ${q['usd_per_s']:.4f}/s" if q['usd_per_s'] else '') + ')')
    L.append(f"  list ${q['usd_total_list']:.4f} — the ${q['usd_total']:.4f} above assumes the "
             f"{q['discount']:.0%} discount recorded {q['discount_as_of']} is STILL LIVE; if it has "
             f"lapsed the batch costs the list figure.")
    if q['metered'] and q['tokens_ceiling'] != q['tokens']:
        L.append(f"  ceiling ${q['usd_ceiling_each_list'] * (1 - q['discount']) * q['seeds']:.4f} — the "
                 f"vendor formula carries no extra frame, but ByteDance's did on monid (measured, "
                 f"+1 frame). No Higgsfield receipt has settled it yet.")
    if balance is not None:
        L.append(f"  wallet {balance['usd']:.2f} USD / {balance['credits']:.1f} cr → "
                 f"{balance['usd'] - q['usd_total']:.2f} USD / "
                 f"{balance['credits'] - q['credits_total']:.1f} cr   (LOCAL LEDGER — the API exposes "
                 f"no balance endpoint, so this is the only copy)")
    return '\n'.join(L)


# ── the wallet ledger ───────────────────────────────────────────────────────────────────────────────
def ledger_load(path=None):
    p = path or LEDGER
    if not os.path.exists(p):
        return {'credit_usd': CREDIT_USD, 'entries': []}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def ledger_append(rec, path=None):
    """Append-only, and written before anything that could fail. The wallet has no remote copy."""
    p = path or LEDGER
    os.makedirs(os.path.dirname(p), exist_ok=True)
    d = ledger_load(p)
    rec.setdefault('ts', time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    d['entries'].append(rec)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, p)
    return rec


def balance(path=None):
    """USD and credits, from LOADs minus SPENDs plus REFUNDs. `failed`, `nsfw` and a successfully
    cancelled `queued` request are NOT charged and auto-refund, so a poller that never writes the
    refund leaves this ledger drifting low on every refusal — which is why hf_api_poll.py writes one."""
    d = ledger_load(path)
    cu = d.get('credit_usd') or CREDIT_USD
    usd = cr = 0.0
    for e in d['entries']:
        sign = 1 if e['kind'] in ('load', 'refund') else -1
        usd += sign * float(e.get('usd') or 0)
        cr += sign * float(e.get('credits') if e.get('credits') is not None
                           else (float(e.get('usd') or 0) / cu))
    spent = sum(float(e.get('usd') or 0) for e in d['entries'] if e['kind'] == 'spend')
    refunded = sum(float(e.get('usd') or 0) for e in d['entries'] if e['kind'] == 'refund')
    return {'usd': usd, 'credits': cr, 'credit_usd': cu, 'entries': len(d['entries']),
            'spent': spent, 'refunded': refunded,
            'loaded': sum(float(e.get('usd') or 0) for e in d['entries'] if e['kind'] == 'load')}


def spend(usd, credits=None, **rec):
    rec.update({'kind': 'spend', 'usd': round(float(usd), 6),
                'credits': round(float(credits if credits is not None else usd / CREDIT_USD), 4)})
    return ledger_append(rec)


def refund(usd, credits=None, **rec):
    rec.update({'kind': 'refund', 'usd': round(float(usd), 6),
                'credits': round(float(credits if credits is not None else usd / CREDIT_USD), 4)})
    return ledger_append(rec)


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')

    q = sub.add_parser('quote', help='the computed cost line (no network, no spend)')
    q.add_argument('--model', default='seedance')
    q.add_argument('--resolution', default='480p', choices=list(RASTER))
    q.add_argument('--duration', type=float, default=5, help='generated seconds')
    q.add_argument('--input-seconds', type=float, default=0,
                   help='source seconds for video-edit / video-extend / a video ref — THEY BILL')
    q.add_argument('--seeds', type=int, default=1)
    q.add_argument('--endpoint', default='reference-to-video')
    q.add_argument('--video-ref', action='store_true', help='a VIDEO reference rides along → 0.6× tier')
    q.add_argument('--refs', type=int, default=0, help='reference image count (H3 surcharges past 5)')

    b = sub.add_parser('balance', help='the wallet, from the local ledger (no endpoint exists)')
    b.add_argument('--json', action='store_true')

    ld = sub.add_parser('load', help='record a credit purchase')
    ld.add_argument('--usd', type=float, required=True)
    ld.add_argument('--credits', type=float, help='credits received; sets the wallet $/cr rate')
    ld.add_argument('--note', default='')

    e = sub.add_parser('estimate', help='the FREE vendor oracle — read the TYPE, never assume a number')
    e.add_argument('--endpoint', required=True)
    e.add_argument('--body', default='{}')

    m = sub.add_parser('models', help='GET /models — the authoritative per-account catalog')
    m.add_argument('--grep', default='')
    a = ap.parse_args()

    if a.cmd == 'quote':
        Q = quote(a.model, a.resolution, a.duration, a.input_seconds, a.seeds,
                  a.endpoint, a.video_ref, a.refs)
        bal = balance()
        print(cost_line(Q, bal if bal['entries'] else None))
        if not bal['entries']:
            print(f'  wallet: NO LEDGER at {LEDGER} — record the purchase first: '
                  f'hf_api.py load --usd <paid> --credits <received>')
        return

    if a.cmd == 'balance':
        bal = balance()
        if a.json:
            print(json.dumps(bal, indent=1)); return
        if not bal['entries']:
            print(f'no ledger at {LEDGER}. The API exposes NO balance endpoint and '
                  f'`higgsfield account status` reports the FROZEN PLAN wallet, not this one — so an '
                  f'unrecorded wallet is UNKNOWABLE, not merely untracked.\n'
                  f'  hf_api.py load --usd 115 --credits 1840'); return
        print(f"wallet ${bal['usd']:.2f} / {bal['credits']:.1f} cr  @ ${bal['credit_usd']}/cr  "
              f"(loaded ${bal['loaded']:.2f} · spent ${bal['spent']:.4f} · refunded "
              f"${bal['refunded']:.4f} · {bal['entries']} entries)\n  {LEDGER}\n"
              f"  ESTIMATES, not receipts: Seedance returns no number, so every spend line is this "
              f"file's own computation. A settled receipt is what would correct it.")
        return

    if a.cmd == 'load':
        d = ledger_load()
        if a.credits:
            d['credit_usd'] = round(a.usd / a.credits, 6)
            os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
            with open(LEDGER, 'w', encoding='utf-8') as f:
                json.dump(d, f, indent=1)
        ledger_append({'kind': 'load', 'usd': a.usd, 'credits': a.credits, 'note': a.note})
        bal = balance()
        print(f"loaded ${a.usd:.2f}" + (f" = {a.credits:g} cr @ ${bal['credit_usd']}/cr" if a.credits else '')
              + f"  → wallet ${bal['usd']:.2f} / {bal['credits']:.1f} cr")
        return

    if a.cmd == 'estimate':
        code, out = api('POST', f"/estimate/{a.endpoint.lstrip('/')}", json.loads(a.body))
        print(f'HTTP {code}')
        if isinstance(out, dict) and out.get('type') == 'description':
            print('TOKEN-METERED — no number comes back. The formula, verbatim:\n  '
                  + str(out.get('pricing_description', '')).strip()
                  + '\n→ use `hf_api.py quote` to compute the cost line.')
        elif isinstance(out, dict) and 'usd' in out:
            d = out.get('discount') or {}
            print(f"FIXED PRICE — credits {out.get('credits')} · usd {out['usd']} (POST-discount)"
                  + (f" · discount {d.get('percentage')}% = ${d.get('usd')} "
                     f"(list ${float(out['usd']) + float(d.get('usd') or 0):.4f})" if d else ''))
        else:
            print(json.dumps(out, indent=1) if not isinstance(out, str) else out)
        return

    if a.cmd == 'models':
        code, out = api('GET', '/models')
        if str(code) != '200':
            print(f'HTTP {code}', json.dumps(out)[:400] if not isinstance(out, str) else out); return
        # {"total": N, "items": [{slug, title, operation_type, output_type, base_credits, …}]} —
        # measured 2026-09-18. `base_credits` is a DEAD field, "0.0000" on every row: never read a
        # price out of this catalog, only the slug set.
        items = out if isinstance(out, list) else (out.get('items') or out.get('models') or
                                                   out.get('data') or [])
        n = 0
        for it in items:
            s = it if isinstance(it, str) else json.dumps(it)
            if a.grep and a.grep.lower() not in s.lower():
                continue
            n += 1
            if isinstance(it, str):
                print(it)
            else:
                print(f"{it.get('slug') or it.get('id') or '?':<58} {(it.get('title') or '')[:40]:<42}"
                      f"{','.join(it.get('operation_type') or [])}")
        print(f"— {n} of {out.get('total', len(items)) if isinstance(out, dict) else len(items)} models "
              f"(the console is authoritative; /docs/openapi.json is NOT)")
        return

    ap.print_help()


if __name__ == '__main__':
    main()
