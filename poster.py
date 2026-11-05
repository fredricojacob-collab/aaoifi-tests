#!/usr/bin/env python3
"""
AAOIFI testlarini (CPSS uslubi) Telegram kanaliga yuboruvchi skript.

Har ishga tushganda navbatdagi BATCH_SIZE ta testni yuboradi va qaysilari
yuborilganini state.json faylida (test ID raqamlari bo'yicha) saqlaydi.

Ko'rinish:
  * Qisqa test (savol va variantlar Telegram poll'iga sig'sa) -> bitta quiz poll,
    variantlar to'liq matn bilan.
  * Uzun test -> avval CPSS mock ko'rinishidagi xabar (Question: N, A. B. C. D.),
    so'ng unga javob tariqasida A/B/C/D (yoki True/False) tugmali quiz poll.

Ishlatish:
  python poster.py --once        # navbatdagi to'plam (GitHub Actions uchun)
  python poster.py --loop        # to'xtovsiz, har soatda (kompyuter/server uchun)
  python poster.py --test        # bitta sinov testi (holat o'zgarmaydi)
  python poster.py --status      # nechta yuborilgan / qolgan
  python poster.py --once --dry-run   # yubormasdan ko'rsatish

Muhit o'zgaruvchilari:
  TELEGRAM_BOT_TOKEN   @BotFather bergan token (MAJBURIY, kodga yozmang)
  TELEGRAM_CHAT_ID     kanal, standart: @AAOIFItests
  BATCH_SIZE           bir martada nechta test, standart: 20
  REPEAT               bank tugasa boshidan boshlash: 1 (standart) yoki 0
  POLL_TAG             har test tagidagi belgi, standart: "🤖 Claude" ("" = belgisiz)
"""
import argparse
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(HERE, "questions.json")
STATE_FILE = os.path.join(HERE, "state.json")

API_BASE = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@AAOIFItests").strip()
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "20"))
REPEAT = os.environ.get("REPEAT", "1").strip() not in ("0", "false", "no", "")
POLL_TAG = os.environ.get("POLL_TAG", "\U0001F916 Claude")
PAUSE = 3.5  # soniya, har bir xabardan keyin (kanal uchun daqiqasiga ~20 xabar chegarasi)

# Telegram chegaralari (UTF-16 birliklarida hisoblanadi)
MAX_Q, MAX_OPT, MAX_EXPL = 300, 100, 200
LETTERS = "ABCD"


def u16(s):
    return len(s.encode("utf-16-le")) // 2


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            st = json.load(f)
    else:
        st = {}
    st.setdefault("sent_ids", [])
    st.setdefault("round", 0)
    st.setdefault("qno", 0)
    st.setdefault("sent_total", 0)
    st.setdefault("last_run", None)
    return st


def save_state(state):
    state["next"] = len(state["sent_ids"])
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def api(method, payload, retries=5):
    if not TOKEN:
        sys.exit("XATO: TELEGRAM_BOT_TOKEN o'rnatilmagan.")
    url = f"{API_BASE}/bot{TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                info = json.loads(body)
            except ValueError:
                info = {"description": body}
            if e.code == 429:
                wait = int(info.get("parameters", {}).get("retry_after", 30)) + 1
                log(f"Telegram cheklovi (429): {wait} soniya kutilmoqda")
                time.sleep(wait)
                continue
            if 500 <= e.code < 600:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"Telegram xatosi {e.code}: {info.get('description')}")
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"Tarmoq xatosi: {e}; qayta urinish")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{method}: {retries} urinishdan keyin ham bo'lmadi")


def options_for(item, rnd):
    """Variantlar va to'g'ri javob indeksi. Qayta aylanishda o'rni almashtiriladigan
    (fixed_order bo'lmagan) testlarda variantlar siljitiladi."""
    if item["type"] == "tf":
        return ["True", "False"], int(item["answer"])
    opts = list(item["options"])
    ans = int(item["answer"])
    r = rnd % 4
    if r and not item.get("fixed_order"):
        opts = opts[-r:] + opts[:-r]
        ans = (ans + r) % 4
    return opts, ans


def source_line(item, with_title=True):
    """Manba: standart raqami, nomi va band(lar)i."""
    ref = (item.get("ref") or "").strip()
    ref = ref.replace("Basis", "Shari'ah Basis").replace("Shari'ah Shari'ah", "Shari'ah")
    head = f"\U0001F4D6 AAOIFI SS {item['standard']}"
    if with_title and item.get("title"):
        head += f" ({item['title']})"
    return f"{head}, {ref}" if ref else head


def explanation_text(item):
    """Izoh: 1-qator manba (SS raqami va band), keyin qisqa izoh, oxirida belgi."""
    body = item.get("explanation", "")
    for with_title in (True, False):
        src = source_line(item, with_title)
        for tag in ((f"\n\n{POLL_TAG}" if POLL_TAG else ""), ""):
            text = f"{src}\n{body}{tag}"
            if u16(text) <= MAX_EXPL:
                return text
    # juda uzun bo'lsa: manba to'liq qoladi, izoh qisqartiriladi
    src = source_line(item, False)
    room = MAX_EXPL - u16(src) - 2
    cut = body
    while u16(cut) > room:
        cut = cut[: cut.rfind(" ")] if " " in cut else cut[:-1]
    return f"{src}\n{cut}\u2026"


def plan(item, qno, rnd):
    """Bitta test uchun Telegram'ga yuboriladigan xabar(lar)."""
    opts, ans = options_for(item, rnd)
    tag = f"\n\n{POLL_TAG}" if POLL_TAG else ""
    single_q = f"Question {qno}: {item['stem']}{tag}"
    fits = u16(single_q) <= MAX_Q and all(u16(o) <= MAX_OPT for o in opts)
    poll = {"chat_id": CHAT_ID, "type": "quiz", "is_anonymous": True,
            "correct_option_id": ans, "explanation": explanation_text(item)}
    if fits:
        poll.update(question=single_q, options=[{"text": o} for o in opts])
        return None, poll
    # uzun test: CPSS ko'rinishidagi matn + harfli poll
    labels = ["True", "False"] if item["type"] == "tf" else list(LETTERS)
    lines = [f"<b>Question: {qno}</b>", "", html.escape(item["stem"], quote=False), ""]
    for k, o in enumerate(opts):
        lines.append(f"<b>{LETTERS[k]}.</b> {html.escape(o, quote=False)}")
        if item["type"] != "tf":
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    if POLL_TAG:
        lines += ["", html.escape(POLL_TAG, quote=False)]
    text = "\n".join(lines).strip()
    msg = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
           "link_preview_options": {"is_disabled": True}}
    poll.update(question=f"Question {qno}: choose the correct answer",
                options=[{"text": l} for l in labels])
    return msg, poll


def pending_items(questions, state):
    done = set(state["sent_ids"])
    return [q for q in questions if q["id"] not in done]


def send_batch(questions, state, n, dry_run=False):
    pending = pending_items(questions, state)
    if not pending:
        if not REPEAT:
            log(f"Test banki tugadi: {len(questions)} ta testning hammasi yuborilgan.")
            return 0
        state["round"] += 1
        state["sent_ids"] = []
        pending = list(questions)
        log(f"Bank tugadi, {state['round'] + 1}-aylanish boshlandi.")
        if not dry_run:
            save_state(state)
    rnd = state["round"]
    batch = pending[:n]
    log(f"Bank: {len(questions)} ta, yuborilgan: {len(state['sent_ids'])}. Bu safar standartlar: "
        + ", ".join(str(q["standard"]) for q in batch) + (f" | belgi: {POLL_TAG}" if POLL_TAG else ""))
    count = 0
    for i, item in enumerate(batch):
        qno = state["qno"] + 1
        msg, poll = plan(item, qno, rnd)
        if dry_run:
            if msg:
                print("\n--- XABAR ---\n" + msg["text"])
                print("--- POLL --- " + poll["question"] + " | " + "/".join(o["text"] for o in poll["options"])
                      + f" | to'g'ri: {poll['options'][poll['correct_option_id']]['text']}")
            else:
                print("\n--- POLL ---\n" + poll["question"])
                for k, o in enumerate(poll["options"]):
                    print(f"   {LETTERS[k]}) {o['text']}" + ("  <-- to'g'ri" if k == poll["correct_option_id"] else ""))
            state["qno"] = qno
            count += 1
            continue
        if msg:
            res = api("sendMessage", msg)
            mid = res.get("result", {}).get("message_id")
            if mid:
                poll["reply_parameters"] = {"message_id": mid, "allow_sending_without_reply": True}
            time.sleep(1.5)
        api("sendPoll", poll)
        count += 1
        state["sent_ids"].append(item["id"])
        state["qno"] = qno
        state["sent_total"] += 1
        state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_state(state)
        if i < len(batch) - 1:
            time.sleep(PAUSE)
    if not dry_run:
        log(f"{count} ta test yuborildi ({len(state['sent_ids'])}/{len(questions)}).")
    return count


def main():
    p = argparse.ArgumentParser(description="AAOIFI CPSS-style quiz poster")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true")
    g.add_argument("--loop", action="store_true")
    g.add_argument("--test", action="store_true")
    g.add_argument("--status", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    questions = load_questions()
    state = load_state()

    if args.status:
        left = len(pending_items(questions, state))
        hours = -(-left // BATCH_SIZE)
        print(f"Aylanish: {state['round'] + 1} | Jami: {len(questions)} | yuborilgan: {len(state['sent_ids'])} "
              f"| qolgan: {left} (~{hours} soat, ~{hours / 24:.1f} kun) | oxirgi: {state.get('last_run')}")
        return

    if args.test:
        pend = pending_items(questions, state) or questions
        msg, poll = plan(pend[0], 0, state["round"])
        poll["question"] = ("[TEST] " + poll["question"])[:MAX_Q]
        if msg:
            msg["text"] = "[TEST]\n" + msg["text"]
            res = api("sendMessage", msg)
            mid = res.get("result", {}).get("message_id")
            if mid:
                poll["reply_parameters"] = {"message_id": mid, "allow_sending_without_reply": True}
        api("sendPoll", poll)
        log("Sinov testi yuborildi.")
        return

    if args.once:
        send_batch(questions, state, BATCH_SIZE, dry_run=args.dry_run)
        return

    if args.loop:
        log(f"Doimiy rejim: har soatda {BATCH_SIZE} ta test -> {CHAT_ID}. To'xtatish: Ctrl+C")
        while True:
            state = load_state()
            if not pending_items(questions, state) and not REPEAT:
                log("Test banki tugadi, skript to'xtadi.")
                return
            try:
                send_batch(questions, state, BATCH_SIZE)
            except RuntimeError as e:
                log(f"XATO: {e}")
            wait = (17 * 60 - time.time() % 3600) % 3600
            time.sleep(wait if wait > 60 else wait + 3600)


if __name__ == "__main__":
    main()
