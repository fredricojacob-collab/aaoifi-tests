#!/usr/bin/env python3
"""
AAOIFI testlarini Telegram kanaliga quiz poll ko'rinishida yuboruvchi skript.

Har ishga tushganda navbatdagi BATCH_SIZE ta testni yuboradi va qayerda
to'xtaganini state.json faylida saqlaydi.

Ishlatish:
  python poster.py --once        # navbatdagi 20 ta testni yuboradi (GitHub Actions / cron uchun)
  python poster.py --loop        # to'xtovsiz ishlaydi: har soatda 20 ta (kompyuter/server uchun)
  python poster.py --test        # kanalga bitta sinov testi yuboradi (holat o'zgarmaydi)
  python poster.py --status      # nechta yuborilgan / qolganini ko'rsatadi
  python poster.py --once --dry-run   # yubormasdan nima yuborilishini ko'rsatadi

Sozlamalar (muhit o'zgaruvchilari):
  TELEGRAM_BOT_TOKEN   @BotFather bergan token (MAJBURIY, kodga yozmang)
  TELEGRAM_CHAT_ID     kanal, standart: @AAOIFItests
  BATCH_SIZE           bir martada nechta test, standart: 20
  REPEAT               bank tugasa boshidan boshlash: 1 (standart) yoki 0
  TELEGRAM_API_BASE    o'zgartirmang (standart: https://api.telegram.org)

Faqat Python 3.8+ standart kutubxonasi ishlatiladi, hech narsa o'rnatish shart emas.
"""
import argparse
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
# bank tugaganda boshidan qayta boshlash (1 = ha, 0 = to'xtash)
REPEAT = os.environ.get("REPEAT", "1").strip() not in ("0", "false", "no", "")
# Har bir test ostida ko'rinadigan belgi (boshqa botlarnikidan ajratish uchun).
# O'zgartirish: shu qatordagi matnni almashtiring yoki POLL_TAG o'zgaruvchisini bering; "" = belgisiz.
POLL_TAG = os.environ.get("POLL_TAG", "\U0001F916 Claude")
PAUSE_BETWEEN_POLLS = 3.5  # soniya; kanalga daqiqasiga ~20 xabar chegarasidan oshmaslik uchun

# Telegram quiz poll chegaralari
MAX_Q, MAX_OPT, MAX_EXPL = 300, 100, 200


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"next": 0, "round": 0, "sent_total": 0, "last_run": None}


def save_state(state):
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
            # 400/403 va boshqalar - qayta urinishdan foyda yo'q
            raise RuntimeError(f"Telegram xatosi {e.code}: {info.get('description')}")
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"Tarmoq xatosi: {e}; qayta urinish")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{method}: {retries} urinishdan keyin ham bo'lmadi")


def rotate(item, rnd):
    """Qayta aylanishda variantlar o'rnini siljitamiz, javoblar takrorlanmasin."""
    r = rnd % 4
    opts = item["options"]
    options = opts[-r:] + opts[:-r] if r else list(opts)
    answer = (int(item["answer"]) + r) % 4
    return options, answer


def build_poll(item, rnd=0):
    question = f"[SS {item['standard']}] {item['q']}"
    if POLL_TAG:
        question = f"{question}\n\n{POLL_TAG}"
    options, answer = rotate(item, rnd)
    explanation = item["explanation"]
    if POLL_TAG and len(explanation) + len(POLL_TAG) + 5 <= MAX_EXPL:
        explanation = f"{explanation}\n\n{POLL_TAG}"
    payload = {
        "chat_id": CHAT_ID,
        "question": question[:MAX_Q],
        "options": [{"text": o[:MAX_OPT]} for o in options],
        "type": "quiz",
        "correct_option_id": answer,
        "is_anonymous": True,
        "explanation": explanation[:MAX_EXPL],
    }
    return payload


def send_batch(questions, state, n, dry_run=False):
    if state["next"] >= len(questions):
        if not REPEAT:
            log(f"Test banki tugadi: {len(questions)} ta testning hammasi yuborilgan.")
            return 0
        state["round"] = state.get("round", 0) + 1
        state["next"] = 0
        log(f"Bank tugadi, {state['round'] + 1}-aylanish boshlandi (variantlar o'rni almashtirildi).")
        if not dry_run:
            save_state(state)
    start = state["next"]
    rnd = state.get("round", 0)
    batch = questions[start:start + n]
    sent = 0
    for i, item in enumerate(batch):
        payload = build_poll(item, rnd)
        if dry_run:
            letters = "ABCD"
            print(f"\n#{start + i + 1} {payload['question']}")
            for k, o in enumerate(payload["options"]):
                o = o["text"]
                mark = "  <-- to'g'ri" if k == payload["correct_option_id"] else ""
                print(f"   {letters[k]}) {o}{mark}")
            sent += 1
            continue
        api("sendPoll", payload)
        sent += 1
        # har bir muvaffaqiyatli yuborishdan keyin holatni saqlaymiz,
        # shunda uzilish bo'lsa ham test qayta yuborilmaydi
        state["next"] = start + sent
        state["sent_total"] = state.get("sent_total", 0) + 1
        state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_state(state)
        if i < len(batch) - 1:
            time.sleep(PAUSE_BETWEEN_POLLS)
    if not dry_run:
        log(f"{sent} ta test yuborildi ({state['next']}/{len(questions)}).")
    return sent


def main():
    p = argparse.ArgumentParser(description="AAOIFI quiz poster")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true", help="navbatdagi to'plamni yuborish")
    g.add_argument("--loop", action="store_true", help="har soatda yuborib turish")
    g.add_argument("--test", action="store_true", help="bitta sinov testi")
    g.add_argument("--status", action="store_true", help="holatni ko'rsatish")
    p.add_argument("--dry-run", action="store_true", help="yubormasdan ko'rsatish")
    args = p.parse_args()

    questions = load_questions()
    state = load_state()

    if args.status:
        left = len(questions) - state["next"]
        hours = -(-left // BATCH_SIZE)
        print(f"Aylanish: {state.get('round', 0) + 1} | Jami: {len(questions)} | yuborilgan: {state['next']} | qolgan: {left} "
              f"(~{hours} soat, ~{hours / 24:.1f} kun) | oxirgi: {state.get('last_run')}")
        return

    if args.test:
        item = questions[min(state["next"], len(questions) - 1)]
        payload = build_poll(item, state.get("round", 0))
        payload["question"] = ("[TEST] " + payload["question"])[:MAX_Q]
        res = api("sendPoll", payload)
        log("Sinov testi yuborildi." if res.get("ok") else f"Javob: {res}")
        return

    if args.once:
        send_batch(questions, state, BATCH_SIZE, dry_run=args.dry_run)
        return

    if args.loop:
        log(f"Doimiy rejim: har soatda {BATCH_SIZE} ta test -> {CHAT_ID}. To'xtatish: Ctrl+C")
        while True:
            state = load_state()
            if state["next"] >= len(questions) and not REPEAT:
                log("Test banki tugadi, skript to'xtadi.")
                return
            try:
                send_batch(questions, state, BATCH_SIZE)
            except RuntimeError as e:
                log(f"XATO: {e}")
            # keyingi soat boshigacha kutish
            now = time.time()
            time.sleep(3600 - (now % 3600) + 5)


if __name__ == "__main__":
    main()
