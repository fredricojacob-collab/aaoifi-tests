# AAOIFI testlari: Telegram kanalga avtomatik yuborish

Ushbu paketdagi skript **@AAOIFItests** kanaliga har soatda **20 tadan** test joylaydi. Testlar Telegram viktorinasi (quiz poll) ko'rinishida chiqadi: o'quvchi variantni bosgach, to'g'ri javob va qisqa izoh ko'rsatiladi.

| Fayl | Vazifasi |
|---|---|
| `questions.json` | Test banki: 2 486 ta test, AAOIFI Shari'ah Standards 1–61 bo'yicha, standartlar tartibida |
| `questions_review.csv` | Testlarni Excel'da ko'rib chiqish uchun nusxa (bot bu fayldan foydalanmaydi) |
| `poster.py` | Testlarni yuboruvchi skript |
| `state.json` | Nechta test yuborilganini saqlaydigan fayl (o'zgartirmang) |
| `.github/workflows/post.yml` | GitHub'da har soatda ishga tushirish sozlamasi |

Soatiga 20 tadan, sutkasiga 24 marta yuborilganda bank taxminan **5 kunga** yetadi. Bank tugagach, skript testlarni avtomatik ravishda boshidan qayta yuboradi va har aylanishda variantlarning o'rnini o'zgartiradi, shuning uchun to'g'ri javob avvalgi harfda qolmaydi. Agar qayta yuborish kerak bo'lmasa, `REPEAT` = `0` o'zgaruvchisini qo'shing (pastda ko'rsatilgan).

---

## 1-qadam. Bot yaratish (5 daqiqa)

1. Telegram'da **@BotFather**'ni oching, `/newbot` buyrug'ini yuboring, botga nom va username bering.
2. BotFather sizga **token** beradi (`123456789:AA...` ko'rinishida). Uni hech kimga yubormang, chatlarga ham joylamang.
3. **@AAOIFItests** kanalini oching: *Manage channel → Administrators → Add admin*, botingizni toping va **Post messages** huquqini yoqing.

## 2-qadam. GitHub'ga joylash (bepul, kompyuter yoqiq turishi shart emas)

1. https://github.com saytidan ro'yxatdan o'ting.
2. **New repository** tugmasini bosing. Nomini, masalan, `aaoifi-tests` qo'ying va **Private** holatini tanlang, shunda testlar ochiq bo'lmaydi. Keyin *Create repository* tugmasini bosing.
3. *uploading an existing file* havolasini bosing va `questions.json`, `questions_review.csv`, `poster.py`, `state.json`, `README.md` fayllarini tashlang. So'ng *Commit changes* tugmasini bosing.
4. Workflow faylini qo'shing. U nuqta bilan boshlanadigan yashirin papkada bo'lgani uchun alohida yaratiladi:
   *Add file → Create new file*. Nom maydoniga aynan `.github/workflows/post.yml` deb yozing. Paketdagi `.github/workflows/post.yml` faylini Bloknotda ochib, butun matnini nusxa qilib joylang va *Commit changes* tugmasini bosing.
5. Tokenni xavfsiz saqlang: *Settings → Secrets and variables → Actions → New repository secret*.
   - Name: `TELEGRAM_BOT_TOKEN`
   - Secret: BotFather bergan token
6. Ruxsat bering: *Settings → Actions → General → Workflow permissions* bo'limida **Read and write permissions** ni tanlang va *Save* tugmasini bosing.

## 3-qadam. Ishga tushirish

1. **Actions** bo'limiga o'ting. Agar so'ralsa, *I understand my workflows, go ahead and enable them* tugmasini bosing.
2. Chapdagi ro'yxatdan **AAOIFI testlarini yuborish** ni tanlang, so'ng **Run workflow → Run workflow** tugmasini bosing.
3. Bir daqiqa ichida kanalga 20 ta test chiqishi kerak. Shundan keyin skript har soatda o'zi ishlaydi.

> GitHub rejali ishlarni ba'zan 5–20 daqiqa kechiktirib ishga tushiradi. Bu odatiy hol.

## Boshqarish

- **Vaqtincha to'xtatish:** *Actions → AAOIFI testlarini yuborish → ⋯ → Disable workflow*. Davom ettirish uchun *Enable workflow* ni bosing.
- **Bir martada yuboriladigan testlar sonini o'zgartirish:** *Settings → Secrets and variables → Actions → Variables → New repository variable* orqali `BATCH_SIZE` = `10` (yoki boshqa son) qo'shing.
- **Bank tugaganda to'xtatish (qayta aylantirmaslik):** `REPEAT` = `0` o'zgaruvchisini qo'shing.
- **Boshqa kanalga yuborish:** xuddi shu joyda `TELEGRAM_CHAT_ID` = `@boshqa_kanal` o'zgaruvchisini qo'shing.
- **Qaysi testgacha yuborilganini ko'rish:** `state.json` faylini oching. Undagi `next` qiymati yuborilgan testlar sonini bildiradi.
- **Boshidan qayta boshlash:** `state.json` faylini tahrirlab, unda `"next": 0` deb yozing va saqlang.

## Xarajat

Private repository'da GitHub oyiga 2 000 daqiqa bepul ishlash vaqti beradi. Bu skript bir ishga tushganda 1–2 daqiqa ishlaydi, ya'ni oyiga taxminan 720–1 440 daqiqa sarflanadi. Demak, bepul limit ichida qoladi. Public repository'da esa umuman cheklov yo'q, lekin u holda testlarni hamma ko'ra oladi.

## Muqobil yo'l: o'z kompyuteringizda yoki serverda ishlatish

Python 3.8 yoki undan yangi versiya kerak, qo'shimcha hech narsa o'rnatish shart emas.

Windows (PowerShell):
```powershell
$env:TELEGRAM_BOT_TOKEN = "TOKENINGIZ"
python poster.py --test     # kanalga bitta sinov testi
python poster.py --loop     # har soatda 20 tadan, oyna ochiq turishi kerak
```

Linux / macOS:
```bash
export TELEGRAM_BOT_TOKEN="TOKENINGIZ"
python3 poster.py --loop
```

Boshqa buyruqlar:
- `python poster.py --status` nechta test yuborilgani va necha kun qolganini ko'rsatadi.
- `python poster.py --once --dry-run` yubormasdan navbatdagi 20 ta testni ekranda ko'rsatadi.

> GitHub va kompyuterni bir vaqtda ishlatmang, aks holda testlar takrorlanadi.

## Muammolar

| Xabar | Sababi va yechimi |
|---|---|
| `Telegram xatosi 400: chat not found` | Kanal manzili noto'g'ri yoki bot kanalga qo'shilmagan |
| `Telegram xatosi 403` / `not enough rights` | Bot kanalda admin emas yoki unda *Post messages* huquqi yo'q |
| `Telegram xatosi 401: Unauthorized` | Token noto'g'ri, `TELEGRAM_BOT_TOKEN` secret'ini qayta kiriting |
| Actions'da "push" xatosi | 2-qadamdagi 6-bandda **Read and write permissions** yoqilmagan |
