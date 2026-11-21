"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

import { LANG_COOKIE, type Lang } from "./lang";

// Локализация интерфейса: узбекский по умолчанию, русский — по выбору в шапке.
// Выбор хранится в cookie `lang`, поэтому сервер сразу отдаёт страницу на нужном языке (app/layout.tsx).
// Язык ответов ИИ в чате от этого не зависит: модель отвечает на языке вопроса.

export { LANG_COOKIE, parseLang, type Lang } from "./lang";
export const LANGS: { value: Lang; label: string }[] = [
  { value: "uz", label: "O‘z" },
  { value: "ru", label: "Рус" },
];

const uz = {
  // каркас
  "app.name": "Mening hujjatlarim",
  "app.module": "MyGov moduli",
  "app.portal": "Mening hujjatlarim — MyGov moduli",
  "app.proto": "Prototip",
  "app.footer": "Bu — prototip: MyGov ichidagi «Mening hujjatlarim» moduli. Haqiqiy davlat portali emas.",
  "nav.menu": "Menyu",
  "nav.section": "Hujjatlar",
  "nav.documents": "Mening hujjatlarim",
  "nav.alerts": "Bildirishnomalar",
  "nav.sources": "Manbalar",
  "nav.family": "Oila",
  "nav.logout": "Chiqish",
  "nav.lang": "Til",
  // лента
  "feed.lead": "Turli davlat reyestrlaridan to‘plangan hujjatlaringiz — versiyalar tarixi bilan birga. Yangi hujjat paydo bo‘lsa, darhol xabar beramiz.",
  "feed.search": "Nomi yoki raqami bo‘yicha qidirish",
  "feed.count": "{n} ta hujjat",
  "feed.sources": "{n} ta manba",
  "feed.new": "{n} ta yangi",
  "feed.monitor": "Monitoring: {n} ta yangi hujjat",
  "feed.check": "Siz bilan bog‘liqligini tekshiring.",
  "feed.review": "Ko‘rib chiqish",
  "feed.tab.all": "Barchasi",
  "feed.tab.poa_car": "E-ishonchnomalar",
  "feed.tab.poa_notarial": "Notarial ishonchnomalar",
  "feed.tab.notarial_act": "Notarial harakatlar",
  "feed.status.any": "Har qanday holat",
  "feed.badge.new": "YANGI",
  "feed.empty": "Hujjatlar topilmadi",
  "feed.empty.hint": "Manbani ulang (storozh documents connect) yoki demo: storozh documents seed",
  "api.down": "API bilan aloqa yo‘q",
  "api.down.hint": "Backend ishga tushirilganini tekshiring: make db, storozh api",
  // карточка
  "doc.notfound": "Hujjat topilmadi",
  "doc.notfound.hint": "Ro‘yxatga qayting",
  "doc.versions": "{n} versiya",
  "doc.kind": "Turi",
  "doc.your_role": "Sizning rolingiz",
  "doc.object": "Obyekt",
  "doc.issued": "Berilgan sana",
  "doc.valid_until": "Amal qilish muddati",
  "doc.issuer": "Kim tomonidan",
  "doc.first_seen": "Birinchi marta ko‘rildi",
  "ver.title": "Versiyalar tarixi",
  "ver.appeared": "Hujjat paydo bo‘ldi",
  "ver.n": "{n}-versiya",
  "ver.changed": "O‘zgardi:",
  "ver.hide": "yashirish",
  "ver.what": "nima o‘zgardi?",
  "ver.first": "Manbada birinchi marta topildi",
  // источники
  "src.title": "Manbalar",
  "src.subtitle": "Ma’lumotlar qayerdan va qanchalik yangi kelayotgani",
  "src.state.ok": "Ishlayapti",
  "src.state.error": "Xatolik",
  "src.state.expired": "Sessiya tugagan",
  "src.state.disabled": "Ulanmagan",
  "src.last_poll": "oxirgi so‘rov · muvaffaqiyatli: {at}",
  "src.every": "har {n} s",
  "src.refresh": "Yangilash",
  "src.rate": "20 soniyada bir martadan ko‘p emas",
  "src.error": "xato",
  "ago.never": "hali so‘ralmagan",
  "ago.s": "{n} s oldin",
  "ago.m": "{n} daq oldin",
  "ago.h": "{n} soat oldin",
  // ИИ
  "ai.summary": "AI xulosa",
  "ai.pending": "Xulosa tayyorlanmoqda — bir necha soniya…",
  "ai.can": "Boshqa tomon nima qila oladi",
  "ai.risks": "Xavflar",
  "ai.todo": "Nima qilish kerak",
  "ai.error": "Xulosani olishning imkoni bo‘lmadi",
  "chat.title": "AI yordamchi",
  "chat.sub": "Ushbu hujjat bo‘yicha",
  "chat.hello": "Assalomu alaykum. Ushbu hujjat bo‘yicha savollaringizga lex.uz bazasi asosida javob beraman. Savolni o‘zbek yoki rus tilida bering.",
  "chat.placeholder": "Hujjat haqida savol bering...",
  "chat.send": "Yuborish",
  "chat.error": "Javob olishning imkoni bo‘lmadi. Qayta urinib ko‘ring.",
  // вход
  "login.title": "«Mening hujjatlarim»ga kirish",
  "login.lead": "Telegram-bot orqali kirish: havola bir martalik va 5 daqiqa amal qiladi. Bot saytga kirish uchun havola yuboradi.",
  "login.button": "Telegram orqali kirish",
  "login.expired": "Havola eskirgan yoki allaqachon ishlatilgan. Qaytadan kiring.",
  "login.failed": "Kirishni boshlab bo‘lmadi. Qayta urinib ko‘ring.",
  "login.fallback": "Telegram ochilmagan bo‘lsa:",
  // «Сторож»
  "guard.title": "Yuridik himoya",
  "guard.note": "Hujjat bo‘yicha tezkor choralar. Har bir harakat Telegram kodi bilan tasdiqlanadi.",
  "guard.not_me": "Bu men emasman",
  "guard.not_me.hint": "Ishonchnomani bekor qilish",
  "guard.pause": "Pauza (31-modda)",
  "guard.pause.hint": "Notariusga ariza",
  "guard.claim": "Da’vo arizasi",
  "guard.claim.hint": "Sudga qoralama",
  "guard.me": "Bu men",
  "guard.me.hint": "Men amalga oshirdim",
  "alerts.title": "Ogohlantirishlar",
  "alerts.subtitle": "Muhimlik bo‘yicha ro‘yxat, «Bu men» va «Bu men emasman» tugmalari",
  "family.title": "Oila",
  "family.subtitle": "Mening ma’lumotlarimga kim kira oladi va men kimnikiga",
  "action.title": "Harakat jarayoni",
  // справочники
  "kind.notarial_act": "Notarial harakat",
  "kind.poa_notarial": "Notarial ishonchnoma",
  "kind.poa_car": "Avtomobilga e-ishonchnoma",
  "kind.ban": "Taqiq",
  "kind.real_estate_right": "Ko‘chmas mulk huquqi",
  "kind.vehicle": "Avtomobil",
  "kind.loan": "Kredit",
  "kind.enforcement_case": "Ijro ishi",
  "kind.labor_contract": "Mehnat shartnomasi",
  "kind.application": "Davlat xizmati arizasi",
  "kind.notification": "Bildirishnoma",
  "kind.company": "Yuridik shaxs",
  "kind.tax_assessment": "Soliq hisob-kitobi",
  "status.active": "Amalda",
  "status.completed": "Bajarilgan",
  "status.revoked": "Bekor qilingan",
  "status.expired": "Muddati o‘tgan",
  "status.unknown": "Noma’lum",
  "role.principal": "Ishonch bildiruvchi",
  "role.agent": "Vakil",
  "role.party": "Tomon",
  "role.debtor": "Qarzdor",
  "role.employee": "Xodim",
  "role.you": "(siz)",
  "field.status": "Holat",
  "field.valid_until": "Amal qilish muddati",
  "field.issued_at": "Berilgan sana",
  "field.title": "Nomi",
  "field.owner_role": "Sizning rolingiz",
  "field.object.label": "Obyekt",
  "field.object.id_masked": "Obyekt raqami",
  "field.parties": "Tomonlar",
  "source.mygov.car_poa": "my.gov.uz · avtomobilga e-ishonchnomalar",
  "source.mygov.notarial_history": "Notarial harakatlar tarixi",
  "source.mygov.requests": "my.gov.uz · mening arizalarim",
  "source.soliq.property": "my.soliq.uz · mulk va yer",
  "source.soliq.vehicles": "my.soliq.uz · avtotransport",
  "source.soliq.taxes": "my.soliq.uz · soliqlar",
  "source.birdarcha.company": "Birdarcha.uz · yuridik shaxslarim",
  "source.mygov.career": "my.gov.uz · mehnat faoliyati",
  "source.mygov.notifications": "my.gov.uz · bildirishnomalar",
  "source.vakolat.check": "Vakolat.uz · ishonchnomani tekshirish",
} as const;

export type MessageKey = keyof typeof uz;

const ru: Record<MessageKey, string> = {
  "app.name": "Мои документы",
  "app.module": "Модуль MyGov",
  "app.portal": "Мои документы — модуль MyGov",
  "app.proto": "Прототип",
  "app.footer": "Это прототип: модуль «Мои документы» внутри MyGov. Не настоящий госпортал.",
  "nav.menu": "Меню",
  "nav.section": "Документы",
  "nav.documents": "Мои документы",
  "nav.alerts": "Уведомления",
  "nav.sources": "Источники",
  "nav.family": "Семья",
  "nav.logout": "Выйти",
  "nav.lang": "Язык",
  "feed.lead": "Ваши документы из разных госреестров — с историей версий. Как только появится новый документ, сразу сообщим.",
  "feed.search": "Поиск по названию или номеру",
  "feed.count": "Документов: {n}",
  "feed.sources": "Источников: {n}",
  "feed.new": "Новых: {n}",
  "feed.monitor": "Мониторинг: новых документов — {n}",
  "feed.check": "Проверьте, относится ли он к вам.",
  "feed.review": "Посмотреть",
  "feed.tab.all": "Все",
  "feed.tab.poa_car": "E-доверенности",
  "feed.tab.poa_notarial": "Нотариальные доверенности",
  "feed.tab.notarial_act": "Нотариальные действия",
  "feed.status.any": "Любой статус",
  "feed.badge.new": "НОВОЕ",
  "feed.empty": "Документы не найдены",
  "feed.empty.hint": "Подключите источник (storozh documents connect) или демо: storozh documents seed",
  "api.down": "Нет связи с API",
  "api.down.hint": "Проверьте, что бэкенд запущен: make db, storozh api",
  "doc.notfound": "Документ не найден",
  "doc.notfound.hint": "Вернитесь к списку",
  "doc.versions": "Версий: {n}",
  "doc.kind": "Тип",
  "doc.your_role": "Ваша роль",
  "doc.object": "Объект",
  "doc.issued": "Дата выдачи",
  "doc.valid_until": "Действует до",
  "doc.issuer": "Кем выдан",
  "doc.first_seen": "Впервые замечен",
  "ver.title": "История версий",
  "ver.appeared": "Документ появился",
  "ver.n": "Версия {n}",
  "ver.changed": "Изменилось:",
  "ver.hide": "скрыть",
  "ver.what": "что изменилось?",
  "ver.first": "Впервые найден в источнике",
  "src.title": "Источники",
  "src.subtitle": "Откуда приходят данные и насколько они свежие",
  "src.state.ok": "Работает",
  "src.state.error": "Ошибка",
  "src.state.expired": "Сессия истекла",
  "src.state.disabled": "Не подключён",
  "src.last_poll": "последний опрос · успешно: {at}",
  "src.every": "каждые {n} с",
  "src.refresh": "Обновить",
  "src.rate": "Не чаще одного раза в 20 секунд",
  "src.error": "ошибка",
  "ago.never": "ещё не опрашивался",
  "ago.s": "{n} с назад",
  "ago.m": "{n} мин назад",
  "ago.h": "{n} ч назад",
  "ai.summary": "AI-резюме",
  "ai.pending": "Готовим резюме — несколько секунд…",
  "ai.can": "Что может другая сторона",
  "ai.risks": "Риски",
  "ai.todo": "Что делать",
  "ai.error": "Не удалось получить резюме",
  "chat.title": "AI-помощник",
  "chat.sub": "По этому документу",
  "chat.hello": "Здравствуйте. Отвечу на вопросы по этому документу на основе базы lex.uz. Спрашивайте на узбекском или русском.",
  "chat.placeholder": "Задайте вопрос о документе...",
  "chat.send": "Отправить",
  "chat.error": "Не удалось получить ответ. Попробуйте ещё раз.",
  "login.title": "Вход в «Мои документы»",
  "login.lead": "Вход через Telegram-бота: ссылка одноразовая и действует 5 минут. Бот пришлёт ссылку для входа на сайт.",
  "login.button": "Войти через Telegram",
  "login.expired": "Ссылка устарела или уже использована. Войдите ещё раз.",
  "login.failed": "Не удалось начать вход. Попробуйте ещё раз.",
  "login.fallback": "Если Telegram не открылся:",
  "guard.title": "Юридическая защита",
  "guard.note": "Быстрые меры по документу. Каждое действие подтверждается кодом из Telegram.",
  "guard.not_me": "Это не я",
  "guard.not_me.hint": "Отозвать доверенность",
  "guard.pause": "Пауза (ст. 31)",
  "guard.pause.hint": "Заявление нотариусу",
  "guard.claim": "Исковое заявление",
  "guard.claim.hint": "Черновик в суд",
  "guard.me": "Это я",
  "guard.me.hint": "Я это оформил(а)",
  "alerts.title": "Предупреждения",
  "alerts.subtitle": "Список по важности, кнопки «Это я» и «Это не я»",
  "family.title": "Семья",
  "family.subtitle": "Кто имеет доступ к моим данным и к чьим имею я",
  "action.title": "Ход действия",
  "kind.notarial_act": "Нотариальное действие",
  "kind.poa_notarial": "Нотариальная доверенность",
  "kind.poa_car": "E-доверенность на автомобиль",
  "kind.ban": "Запрет",
  "kind.real_estate_right": "Право на недвижимость",
  "kind.vehicle": "Автомобиль",
  "kind.loan": "Кредит",
  "kind.enforcement_case": "Исполнительное производство",
  "kind.labor_contract": "Трудовой договор",
  "kind.application": "Заявка на госуслугу",
  "kind.notification": "Уведомление",
  "kind.company": "Юридическое лицо",
  "kind.tax_assessment": "Налоговый расчёт",
  "status.active": "Действует",
  "status.completed": "Исполнен",
  "status.revoked": "Отозван",
  "status.expired": "Истёк",
  "status.unknown": "Неизвестно",
  "role.principal": "Доверитель",
  "role.agent": "Представитель",
  "role.party": "Сторона",
  "role.debtor": "Должник",
  "role.employee": "Сотрудник",
  "role.you": "(вы)",
  "field.status": "Статус",
  "field.valid_until": "Срок действия",
  "field.issued_at": "Дата выдачи",
  "field.title": "Название",
  "field.owner_role": "Ваша роль",
  "field.object.label": "Объект",
  "field.object.id_masked": "Номер объекта",
  "field.parties": "Стороны",
  "source.mygov.car_poa": "my.gov.uz · e-доверенности на авто",
  "source.mygov.notarial_history": "История нотариальных действий",
  "source.mygov.requests": "my.gov.uz · мои заявки",
  "source.soliq.property": "my.soliq.uz · имущество и земля",
  "source.soliq.vehicles": "my.soliq.uz · автотранспорт",
  "source.soliq.taxes": "my.soliq.uz · налоги",
  "source.birdarcha.company": "Birdarcha.uz · мои юрлица",
  "source.mygov.career": "my.gov.uz · трудовая деятельность",
  "source.mygov.notifications": "my.gov.uz · уведомления",
  "source.vakolat.check": "Vakolat.uz · проверка доверенности",
};

const MESSAGES: Record<Lang, Record<MessageKey, string>> = { uz, ru };

export function translate(lang: Lang, key: MessageKey, vars?: Record<string, string | number>): string {
  let s = MESSAGES[lang][key] ?? MESSAGES.uz[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

/** Ключ из справочника по произвольной строке (тип, статус, поле): нет перевода — вернуть fallback. */
export function translateOr(lang: Lang, key: string, fallback: string): string {
  return key in uz ? translate(lang, key as MessageKey) : fallback;
}

type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
  tOr: (key: string, fallback: string) => string;
};

const I18nContext = createContext<Ctx | null>(null);

export function I18nProvider({ initialLang, children }: { initialLang: Lang; children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    document.cookie = `${LANG_COOKIE}=${l}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = l;
  }, []);
  const t = useCallback((key: MessageKey, vars?: Record<string, string | number>) => translate(lang, key, vars), [lang]);
  const tOr = useCallback((key: string, fallback: string) => translateOr(lang, key, fallback), [lang]);
  return <I18nContext.Provider value={{ lang, setLang, t, tOr }}>{children}</I18nContext.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n outside I18nProvider");
  return ctx;
}
