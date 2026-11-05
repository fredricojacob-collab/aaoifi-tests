# AAOIFI testlari: CPSS uslubidagi yangi bank

Bu paketdagi testlar AAOIFI'ning rasmiy **CPSS MOCK v2024** imtihoni uslubida tuzilgan. Ularning formati, savollarning tuzilishi, variantlari va qiyinlik darajasi mock'nikiga o'xshaydi.

| Fayl | Vazifasi |
|---|---|
| `questions.json` | **2 483 ta test**, AAOIFI Shari'ah Standards 1–61 bo'yicha, butun kitob bo'yicha aralash |
| `questions_review.csv` | Testlarni Excel'da ko'rib chiqish uchun nusxa (bot bu fayldan foydalanmaydi) |
| `poster.py` | Testlarni kanalga yuboruvchi skript (yangi versiya) |
| `state.json` | Yangi bank uchun boshlang'ich holat (hisob noldan boshlanadi) |
| `.github/workflows/post.yml` | GitHub'da har soatda (17-daqiqada) ishga tushirish sozlamasi |

## Bankda nimalar bor

- **1 876 ta 4 variantli test (76%) va 607 ta True/False (24%)**. Mock'da ham shu nisbat: 76 ta MCQ va 24 ta True/False.
- **Savollar mock'dagi shakllarda tuzilgan:**
  - "It is impermissible:"
  - "………… is the replacement of a creditor with another:"
  - "except" va "excluding" savollar
  - foizlar, shartlar va tomonlar haqidagi savollar
  - taxminan 10–15% qisqa case.
- **Variantlar standart matniga yaqin yozilgan.** "All of the above are true.", "(a) and (b).", "None of the above is true." kabi variantlar ham bor.
- **To'g'ri javob A, B, C, D variantlariga teng taqsimlangan.** To'g'ri javob eng uzun variant bo'lgan testlar taxminan 21% (mock'da 27%), ya'ni javobni variantning uzunligidan topib bo'lmaydi.
- Har bir testdan keyin bandga havola qilingan qisqa izoh chiqadi.

## Kanalda qanday ko'rinadi

- **Qisqa test** bitta quiz poll bo'lib chiqadi: "Question 15: …" va to'liq variantlar.
- **Uzun test** ikki xabar bo'lib chiqadi. Avval mock ko'rinishidagi xabar keladi: **Question: 16**, savol va **A. B. C. D.** variantlar. So'ng shu xabarga javob tariqasida A/B/C/D (yoki True/False) tugmali quiz poll chiqadi.
- Har bir test tagida **🤖 Claude** belgisi turadi.

## GitHub'ga yuklash

1. **Code** bo'limida **Add file → Upload files** ni bosing.
2. Shu to'rt faylni bir vaqtda tashlang: `poster.py`, `questions.json`, `questions_review.csv`, `state.json`. Keyin **Commit changes** ni bosing.
3. Yuklash paytida Actions'da sariq doira bilan run ishlayotgan bo'lmasin. Agar ishlayotgan bo'lsa, u tugashini kuting.
4. `.github/workflows/post.yml` faylini 1-noyabrdagi oxirgi versiyaga (17-daqiqa jadvali va "Holatni saqlash" qadamida `for i in 1 2 3 4 5` sikli) almashtirgan bo'lsangiz, unga tegmang. Almashtirmagan bo'lsangiz, paketdagi `post.yml` matnini u yerga joylang.
5. **Actions → AAOIFI testlarini yuborish → Run workflow** orqali sinab ko'ring.

## GitHub'dagi bepul vaqt haqida muhim eslatma

Yangi formatda uzun testlar ikki xabardan iborat. Shu sababli har soatlik run taxminan 2–3 daqiqa davom etadi. **Private** repository'da bu oyiga ~2 000–2 200 daqiqa qiladi va GitHub'ning bepul limitidan (2 000 daqiqa) biroz oshishi mumkin. Limit tugasa, oy oxirigacha yuborish to'xtab qoladi.

Eng oson yechim — repository'ni **Public** qilish. Public repository'larda GitHub Actions cheklovsiz bepul. Testlar kanalda baribir ochiq chiqadi, bot tokeni esa Secrets ichida yashirin qoladi.

Qanday qilinadi: **Settings → General** sahifasining eng pastidagi **Danger Zone → Change visibility → Make public**.

Boshqa yo'l: `BATCH_SIZE` o'zgaruvchisini `15` qiling (Settings → Secrets and variables → Actions → Variables).

## Boshqarish

- **Vaqtincha to'xtatish:** Actions → AAOIFI testlarini yuborish → ⋯ → **Disable workflow**.
- **Bir martada yuboriladigan testlar soni:** `BATCH_SIZE` o'zgaruvchisi (standart 20).
- **Bank tugaganda qayta boshlamaslik:** `REPEAT` = `0`. Standart holatda skript bank tugagach boshidan boshlaydi va o'rni almashsa ham bo'ladigan variantlarning tartibini o'zgartiradi.
- **Holat:** `state.json` faylidagi `sent_ids` ro'yxatida yuborilgan testlarning raqamlari saqlanadi. Bu faylni qo'lda o'zgartirmang.
- Bank soatiga 20 tadan yuborilsa, taxminan **5 kunga** yetadi.
