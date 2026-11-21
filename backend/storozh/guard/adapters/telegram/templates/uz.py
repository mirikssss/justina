"""Тексты сообщений бота (uz). Без ФИО, ПИНФЛ, адреса и сумм (FR-G-06); единственная ссылка — на наш домен."""

ALERT = {
    "G1": "⚠️ Sizning nomingizdan ishonchnoma berildi{object}. Bu sizmisiz?",
    "G2": "⚠️ Sizning ishtirokingizda notarial harakat amalga oshirildi. Bu sizmisiz?",
    "G3": "ℹ️ Hujjat holati o'zgardi.",
    "G4": "ℹ️ Ishonchnoma muddati tez orada tugaydi{object}.",
    "G5": "🔔 Hujjat manbadan yo'qoldi. Kabinetni tekshiring.",
    "G6": "🔔 Manba uzildi: ma'lumotlar yangilanmayapti. Manbani qayta ulang.",
    "G7": "⚠️ Qarindoshingizda muhim ogohlantirish. Ko'rish uchun oching.",
}
ALERT_FALLBACK = "🔔 Hujjatlaringizda yangi hodisa."
OBJECT = " ({object})"

BUTTON = {
    "not_me": "Bu men emasman",
    "me": "Bu men",
    "open": "Ochish",
    "reconnect": "Qayta ulash",
}

VERDICT_ME = "✅ Belgilandi: bu siz. Ogohlantirish yopildi."
VERDICT_NOT_ME = "Hujjat kartasini oching va «Bekor qilish» tugmasini bosing — tasdiqlash kodi shu yerga keladi."
VERDICT_DONE = "Javob qabul qilindi."
CALLBACK_BAD = "Tugma eskirgan yoki yaroqsiz."

CODE = ("🔐 Tasdiqlash kodi: <b>{code}</b>\n"
        "Amal: {action}.\n"
        "Kod 2 daqiqa amal qiladi. Uni hech kimga aytmang — biz hech qachon kod so'ramaymiz.")
ACTION = {"revoke_car_poa": "avto ishonchnomasini bekor qilish"}
ACTION_DONE = "✅ Bekor qilindi. Manba tomonidan tasdiqlandi."
ACTION_FAILED = "❌ Harakat bajarilmadi. Kabinetni tekshiring."

LINK_OK = "✅ Telegram ulandi. Muhim ogohlantirishlar va tasdiqlash kodlari shu yerga keladi."
LINK_BAD = "Havola eskirgan yoki allaqachon ishlatilgan. Saytda «Telegramni ulash»ni qaytadan bosing."
LINK_TAKEN = "Bu Telegram boshqa kabinetga ulangan."
LOGIN_OK = "Saytga kirish uchun havola (bir martalik, 5 daqiqa):"
LOGIN_BUTTON = "Saytga kirish"
LOGIN_BAD = "Kirish havolasi eskirgan yoki bu Telegram kabinetga ulanmagan. Saytda qaytadan urinib ko'ring."
HELP = "Bu «Mening hujjatlarim» qo'riqchisi boti. Uni saytdagi havola orqali ulang."
