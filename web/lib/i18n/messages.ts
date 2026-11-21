// Переключатель uz/ru (TODO FR-G-15). Лёгкая замена next-intl без новой зависимости и без
// locale-роутинга: исходный язык кабинета — узбекский, узбекская строка и есть ключ. Для ru берём
// перевод отсюда, при отсутствии — показываем узбекский (graceful fallback). Коллизии одинаковых
// узбекских строк с разным переводом разводятся контекстом: ключ "<ctx>::<uz>".

export type Locale = "uz" | "ru";
export const LOCALES: Locale[] = ["uz", "ru"];
export const LOCALE_NAME: Record<Locale, string> = { uz: "O‘zbekcha", ru: "Русский" };
export const LOCALE_SHORT: Record<Locale, string> = { uz: "O‘z", ru: "Рус" };

// uz → ru. Ключи — ровно те узбекские строки, что стоят в коде.
export const RU: Record<string, string> = {
  // --- Каркас / Shell ---
  "Mening hujjatlarim": "Мои документы",
  "Bildirishnomalar": "Уведомления",
  "Manbalar": "Источники",
  "Oila": "Семья",
  "MyGov moduli": "Модуль MyGov",
  "Hujjatlar": "Документы",
  "Mening hujjatlarim — MyGov moduli": "Мои документы — модуль MyGov",
  "Prototip": "Прототип",
  "Chiqish": "Выход",
  "Menyu": "Меню",
  "Bu —": "Это —",
  "prototip": "прототип",
  "MyGov ichidagi «Mening hujjatlarim» moduli. Haqiqiy davlat portali emas.":
    "модуль «Мои документы» внутри MyGov. Не настоящий государственный портал.",

  // --- Guard: severity / rules / статусы ---
  "Muhim": "Важно",
  "Yuqori": "Высокая",
  "Ma'lumot": "Информация",
  "Yangi ishonchnoma": "Новая доверенность",
  "Notarial harakat": "Нотариальное действие",
  "Holat o'zgardi": "Статус изменился",
  "Muddati tugayapti": "Истекает срок",
  "Hujjat yo'qoldi": "Документ пропал",
  "Manba uzildi": "Источник отключён",
  "Oila nusxasi": "Копия для семьи",
  "Yangi": "Новое",
  "Ko'rilgan": "Просмотрено",
  "Yopilgan": "Закрыто",

  // --- Guard: машина состояний действия ---
  "So'ralgan": "Запрошено",
  "Harakat so'raldi": "Действие запрошено",
  "Tasdiq kutilmoqda": "Ожидает подтверждения",
  "Telegramga kod yuborildi": "Код отправлен в Telegram",
  "Tasdiqlandi": "Подтверждено",
  "Kod qabul qilindi": "Код принят",
  "Bajarilmoqda": "Выполняется",
  "Manbada amalga oshirilmoqda": "Выполняется в источнике",
  "Tekshirilmoqda": "Проверяется",
  "Natija manbadan tekshirilmoqda": "Результат проверяется в источнике",
  "Bajarildi": "Выполнено",
  "Manba tomonidan tasdiqlandi": "Подтверждено источником",
  "Xatolik": "Ошибка",
  "Bajarilmadi — kabinetni tekshiring": "Не выполнено — проверьте кабинет",
  "Muddati tugadi": "Срок истёк",
  "Tasdiqlash muddati o'tdi": "Срок подтверждения истёк",
  "Avto ishonchnomasini bekor qilish": "Отзыв доверенности на авто",

  // --- Guard: scopes (Oila) ---
  "Hujjatlarni ko'rish": "Просмотр документов",
  "Mening hujjatlarim ro'yxatini ko'radi": "Видит список моих документов",
  "Ogohlantirishlarni olish": "Получать уведомления",
  "Muhim ogohlantirishlar nusxasini oladi": "Получает копию важных уведомлений",

  // --- Guard: AlertsPage ---
  "Barchasi": "Все",
  "Ogohlantirishlar": "Уведомления",
  "Hujjatlaringizdagi o'zgarishlar — eng muhimidan boshlab":
    "Изменения в ваших документах — от самых важных",
  "Ogohlantirishlar yo'q": "Уведомлений нет",
  "Yangi hodisa paydo bo'lsa, shu yerda ko'rinadi":
    "Когда появится новое событие, оно будет здесь",
  "Bu men emasman": "Это не я",
  "Bu men": "Это я",
  "Manbani qayta ulash": "Переподключить источник",
  "Ochish": "Открыть",
  "Hujjatni ochish": "Открыть документ",
  "Bu men edi": "Это был я",
  "Bu men emas edim": "Это был не я",
  "Belgilandi: bu men": "Отмечено: это я",
  "Belgilandi: bu men emasman": "Отмечено: это не я",
  "Saqlanmadi, qaytadan urinib ko'ring": "Не сохранено, попробуйте снова",

  // --- Guard: ConfirmModal ---
  "Tasdiqlash kodi": "Код подтверждения",
  "Bekor qilish": "Отмена",
  "revoke::Bekor qilish": "Отозвать",
  "Tekshirilmoqda…": "Проверяется…",
  "Tasdiqlash": "Подтвердить",
  "Telegramga yuborilgan 6 xonali kodni kiriting.":
    "Введите 6-значный код, отправленный в Telegram.",
  "Kod amal qiladi: {mmss}": "Код действует: {mmss}",
  "Urinishlar: {n}/3": "Попытки: {n}/3",
  "Urinishlar tugadi. Yangi harakat so'rang.":
    "Попытки исчерпаны. Запросите новое действие.",
  "Kod noto'g'ri. Qaytadan kiriting.": "Неверный код. Введите снова.",
  "Tarmoq xatosi. Qaytadan urinib ko'ring.": "Ошибка сети. Попробуйте снова.",

  // --- Guard: ActionPage ---
  "Harakat topilmadi": "Действие не найдено",
  "Ro'yxatga qayting": "Вернитесь к списку",
  "Harakat jarayoni": "Ход действия",
  "Bosqichlar": "Этапы",
  "hozir…": "сейчас…",
  "Natija": "Результат",
  "Bekor qilindi. Natija manbada tasdiqlandi":
    "Отозвано. Результат подтверждён в источнике",
  "Manbadan tasdiq olinmadi. Kabinetni tekshiring.":
    "Подтверждение из источника не получено. Проверьте кабинет.",
  "Tasdiqlash muddati o'tdi. Hujjat kartasidan harakatni qaytadan boshlang.":
    "Срок подтверждения истёк. Начните действие заново с карточки документа.",
  "Bajarilmadi": "Не выполнено",
  "Qadam-baqadam": "Шаг за шагом",
  "Harakat ikki bosqichda tasdiqlanadi: sayt — so'rov, Telegram — kod. Kod faqat sizning ulangan Telegramingizga keladi va 2 daqiqa amal qiladi.":
    "Действие подтверждается в два шага: сайт — запрос, Telegram — код. Код приходит только в ваш подключённый Telegram и действует 2 минуты.",
  "Jarayon jonli yangilanadi — sahifani yopishingiz mumkin.":
    "Процесс обновляется вживую — страницу можно закрыть.",
  "Natija skrinshoti": "Скриншот результата",
  "To'liq ko'rish": "Открыть полностью",

  // --- Guard: FamilyPage ---
  "Ma'lumotlaringizni kim ko'ra oladi va siz kimning ma'lumotini ko'rasiz":
    "Кто видит ваши данные и чьи данные видите вы",
  "Men ulashganlar": "Кому я открыл доступ",
  "Hali hech kimga ulashmagansiz": "Вы ещё никому не открыли доступ",
  "Yuqoridagi kod orqali qarindoshingizni taklif qiling":
    "Пригласите родственника по коду выше",
  "Menga ulashilgan": "Мне открыли доступ",
  "Sizga hech kim ulashmagan": "Вам никто не открыл доступ",
  "Qarindoshingiz bergan kodni yuqorida kiriting":
    "Введите код от родственника выше",
  "Qarindoshni taklif qilish": "Пригласить родственника",
  "Qanday huquq berasiz:": "Какие права даёте:",
  "Taklif kodi yaratildi": "Код приглашения создан",
  "Kodni yaratib bo'lmadi": "Не удалось создать код",
  "Nusxalandi": "Скопировано",
  "Nusxalash": "Копировать",
  "Taklif kodini olish": "Получить код приглашения",
  "Taklif kodini kiritish": "Ввести код приглашения",
  "Qarindoshingiz bergan kodni kiriting — uning lentasini ko'rishni boshlaysiz.":
    "Введите код от родственника — вы начнёте видеть его ленту.",
  "Taklif kodi": "Код приглашения",
  "Ulanildi": "Подключено",
  "Kod noto'g'ri yoki muddati o'tgan": "Код неверен или истёк",
  "Qabul qilish": "Принять",
  "Ruxsat bekor qilindi": "Доступ отозван",
  "Bekor qilib bo'lmadi": "Не удалось отозвать",
  "Faol": "Активно",

  // --- Guard: DocumentGuard ---
  "Yuridik himoya": "Юридическая защита",
  "Hujjat bo'yicha tezkor choralar. Har bir harakat Telegram kodi bilan tasdiqlanadi.":
    "Оперативные меры по документу. Каждое действие подтверждается кодом из Telegram.",
  "Ishonchnomani bekor qilish": "Отозвать доверенность",
  "Pauza (31-modda)": "Пауза (ст. 31)",
  "Notariusga ariza": "Заявление нотариусу",
  "Da'vo arizasi": "Исковое заявление",
  "Sudga qoralama": "Черновик для суда",
  "Men amalga oshirdim": "Я это сделал",
  "Tasdiqlash kodi Telegramga yuborildi": "Код подтверждения отправлен в Telegram",
  "Harakatni boshlab bo'lmadi. Telegram ulanganini tekshiring.":
    "Не удалось начать действие. Проверьте подключение Telegram.",
  "Ariza qoralamasi tayyor": "Черновик заявления готов",
  "Qoralamani yaratib bo'lmadi": "Не удалось создать черновик",
  "Belgilandi: bu men amalga oshirdim": "Отмечено: это сделал я",

  // --- Documents: KIND ---
  "Notarial ishonchnoma": "Нотариальная доверенность",
  "Avtomobilga e-ishonchnoma": "Э-доверенность на авто",
  "Taqiq": "Запрет",
  "Ko'chmas mulk huquqi": "Право на недвижимость",
  "Avtomobil": "Автомобиль",
  "Kredit": "Кредит",
  "Ijro ishi": "Исполнительное производство",
  "Mehnat shartnomasi": "Трудовой договор",
  "Davlat xizmati arizasi": "Заявление на госуслугу",
  "Bildirishnoma": "Уведомление",
  "Yuridik shaxs": "Юридическое лицо",
  "Soliq hisob-kitobi": "Налоговый расчёт",

  // --- Documents: STATUS ---
  "Amalda": "Действует",
  "Bajarilgan": "Исполнен",
  "Bekor qilingan": "Отозван",
  "Muddati o'tgan": "Истёк",
  "Noma'lum": "Неизвестно",

  // --- Documents: SOURCE ---
  "my.gov.uz · avtomobilga e-ishonchnomalar": "my.gov.uz · э-доверенности на авто",
  "Notarial harakatlar tarixi": "История нотариальных действий",
  "my.gov.uz · mening arizalarim": "my.gov.uz · мои заявления",
  "my.gov.uz · bildirishnomalar": "my.gov.uz · уведомления",
  "Vakolat.uz · ishonchnomani tekshirish": "Vakolat.uz · проверка доверенности",

  // --- Documents: ROLE ---
  "Ishonch bildiruvchi (siz)": "Доверитель (вы)",
  "Vakil (siz)": "Представитель (вы)",
  "Tomon": "Сторона",
  "Qarzdor": "Должник",
  "Xodim": "Работник",

  // --- Documents: FIELD ---
  "Holat": "Статус",
  "Amal qilish muddati": "Срок действия",
  "Berilgan sana": "Дата выдачи",
  "Nomi": "Название",
  "Sizning rolingiz": "Ваша роль",
  "Obyekt": "Объект",
  "Obyekt raqami": "Номер объекта",
  "Tomonlar": "Стороны",

  // --- Documents: относительное время ---
  "hali so'ralmagan": "ещё не запрашивалось",

  // --- Documents: DocumentFeed ---
  "Turli davlat reyestrlaridan to'plangan hujjatlaringiz — versiyalar tarixi bilan birga. Yangi hujjat paydo bo'lsa, darhol xabar beramiz.":
    "Ваши документы, собранные из разных госреестров, — вместе с историей версий. Как только появится новый документ, сразу сообщим.",
  "Nomi yoki raqami bo'yicha qidirish": "Поиск по названию или номеру",
  "{n} ta hujjat": "{n} документов",
  "{n} ta manba": "{n} источников",
  "{n} ta yangi": "{n} новых",
  "Monitoring: {n} ta yangi hujjat": "Мониторинг: {n} новых документов",
  "Siz bilan bog'liqligini tekshiring.": "Проверьте, связано ли это с вами.",
  "Ko'rib chiqish": "Рассмотреть",
  "API bilan aloqa yo'q": "Нет связи с API",
  "Backend ishga tushirilganini tekshiring: make db, storozh api":
    "Проверьте, запущен ли backend: make db, storozh api",
  "Hujjatlar topilmadi": "Документы не найдены",
  "Manbani ulang (storozh documents connect) yoki demo: storozh documents seed":
    "Подключите источник (storozh documents connect) или демо: storozh documents seed",
  "YANGI": "НОВОЕ",
  "E-ishonchnomalar": "Э-доверенности",
  "Notarial ishonchnomalar": "Нотариальные доверенности",
  "Notarial harakatlar": "Нотариальные действия",
  "Har qanday holat": "Любой статус",

  // --- Documents: DocumentPage ---
  "Hujjat topilmadi": "Документ не найден",
  "{n} versiya": "{n} версий",
  "Turi": "Тип",
  "Kim tomonidan": "Кем выдан",
  "Birinchi marta ko'rildi": "Впервые замечен",
  "Versiyalar tarixi": "История версий",
  "Hujjat paydo bo'ldi": "Документ появился",
  "{n}-versiya": "Версия {n}",
  "O'zgardi:": "Изменилось:",
  "yashirish": "скрыть",
  "nima o'zgardi?": "что изменилось?",
  "Manbada birinchi marta topildi": "Впервые найдено в источнике",

  // --- Documents: SourcesPage ---
  "Ishlayapti": "Работает",
  "Sessiya tugagan": "Сессия истекла",
  "Ulanmagan": "Не подключён",
  "Ma'lumotlar qayerdan va qanchalik yangi kelayotgani":
    "Откуда и насколько свежие данные",
  "20 soniyada bir martadan ko'p emas": "Не чаще одного раза в 20 секунд",
  "xato": "ошибка",
  "oxirgi so'rov · muvaffaqiyatli:": "последний опрос · успешно:",
  "har {n} s": "каждые {n} с",
  "Yangilash": "Обновить",

  // --- Assistant ---
  "AI xulosa": "AI-резюме",
  "Bu nima · boshqa tomon nima qila oladi · xavflar · nima qilish kerak — havolalar bilan.":
    "Что это · что может сделать другая сторона · риски · что делать — со ссылками.",
  "AI yordamchi": "AI-помощник",
  "Ushbu hujjat bo'yicha": "По этому документу",
  "Assalomu alaykum. Ushbu hujjat bo'yicha savollaringizga lex.uz bazasi asosida javob beraman.":
    "Здравствуйте. Отвечу на ваши вопросы по этому документу на основе базы lex.uz.",
  "Hujjat haqida savol bering...": "Задайте вопрос о документе...",
  "Yuborish": "Отправить",

  // --- Login (заглушка Разработчика 2) ---
  "«Mening hujjatlarim»ga kirish": "Вход в «Мои документы»",
  "Telegram-bot orqali kirish: havola bir martalik va 5 daqiqa amal qiladi.":
    "Вход через Telegram-бота: ссылка одноразовая и действует 5 минут.",
  "Telegram-bot orqali kirish: havola bir martalik va 5 daqiqa amal qiladi. Bot saytga kirish uchun havola yuboradi.":
    "Вход через Telegram-бота: ссылка одноразовая и действует 5 минут. Бот пришлёт ссылку для входа на сайт.",
  "Havola eskirgan yoki allaqachon ishlatilgan. Qaytadan kiring.":
    "Ссылка устарела или уже использована. Войдите ещё раз.",
  "Kirishni boshlab bo'lmadi. Qayta urinib ko'ring.": "Не удалось начать вход. Попробуйте ещё раз.",
  "Telegram ochilmagan bo'lsa:": "Если Telegram не открылся:",
  "Javob olishning imkoni bo‘lmadi. Qayta urinib ko‘ring.": "Не удалось получить ответ. Попробуйте ещё раз.",
  "Telegram orqali kirish": "Войти через Telegram",
  "Telegramni ulash": "Подключить Telegram",
  "Ma'lumotlarni qayta ishlashga rozilik": "Согласие на обработку данных",
  "Rad etish va chiqish": "Отказаться и выйти",
  "Roziman": "Согласен",
  "Xizmat ishlashi uchun quyidagilarga ruxsatingiz kerak:": "Для работы сервиса нужно ваше разрешение на:",
  "Kabinetlaringizdagi hujjatlarni sizning sessiyangiz bilan o'qish (MyGov, soliq, Vakolat)":
    "Чтение документов из ваших кабинетов вашей сессией (MyGov, налоговая, Vakolat)",
  "Ma'lumotlarni shaxsiy kalit bilan shifrlangan holda saqlash; kartochkalarda faqat niqoblar":
    "Хранение данных в зашифрованном виде личным ключом; в карточках — только маски",
  "Ogohlantirish va tasdiqlash kodlarini ulangan Telegramga yuborish":
    "Отправку тревог и кодов подтверждения в подключённый Telegram",
  "AI tushuntirishlari — shaxsiy ma'lumotlarsiz (ism, JSHSHIR, telefon yashiriladi)":
    "Объяснения ИИ — без персональных данных (ФИО, ПИНФЛ, телефон скрываются)",
  "Rozilikni istalgan vaqtda qaytarib olishingiz mumkin: «Ma'lumotlarimni o'chirish» shifrlash kalitini o'chiradi va saqlangan ma'lumotlar o'qib bo'lmaydigan bo'ladi.":
    "Согласие можно отозвать в любой момент: «Удалить мои данные» стирает ключ шифрования, и сохранённые данные становятся нечитаемыми.",
  "Ma'lumotlarimni o'chirish": "Удалить мои данные",
  "Ma'lumotlaringiz o'chirilsinmi?": "Удалить ваши данные?",
  "Ha, o'chirish": "Да, удалить",
  "O'chirib bo'lmadi, qaytadan urinib ko'ring": "Не удалось удалить, попробуйте ещё раз",
  "Shifrlash kalitingiz o'chiriladi: kabinet sessiyalari, hujjatlarning asl ma'lumotlari, Telegram va skrinshotlar o'qib bo'lmaydigan bo'ladi. Barcha qurilmalardan chiqasiz. Buni qaytarib bo'lmaydi.":
    "Ваш ключ шифрования будет удалён: сессии кабинетов, исходные данные документов, Telegram и скриншоты станут нечитаемыми. Вы выйдете со всех устройств. Это нельзя отменить.",
  "Hodisadan Telegramgacha": "От события до Telegram",
  "Telegramga {n} s da": "в Telegram за {n} с",
  "Tasdiqlashdan natijagacha: {n} s": "От подтверждения до результата: {n} с",
  "Botda «Start»ni bosing — havola 10 daqiqa amal qiladi": "Нажмите «Start» в боте — ссылка действует 10 минут",
  "Havolani olib bo'lmadi. Qayta urinib ko'ring.": "Не удалось получить ссылку. Попробуйте ещё раз.",
};
