"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Modal, toast } from "@/components/mygov";
import { api } from "@/lib/api/client";
import { useT } from "@/lib/i18n";

// T9 (ЗРУ-547): согласие на обработку до работы с кабинетом и «Удалить мои данные» (криптоудаление).

const SCOPE_TEXT: Record<string, string> = {
  read_cabinets: "Kabinetlaringizdagi hujjatlarni sizning sessiyangiz bilan o'qish (MyGov, soliq, Vakolat)",
  store_encrypted: "Ma'lumotlarni shaxsiy kalit bilan shifrlangan holda saqlash; kartochkalarda faqat niqoblar",
  notify_telegram: "Ogohlantirish va tasdiqlash kodlarini ulangan Telegramga yuborish",
  ai_explanations: "AI tushuntirishlari — shaxsiy ma'lumotlarsiz (ism, JSHSHIR, telefon yashiriladi)",
};

function useConsent() {
  return useQuery({
    queryKey: ["consent"],
    queryFn: async () => {
      const { data, error } = await api.GET("/me/consent");
      if (error !== undefined || !data) throw error ?? new Error("consent");
      return data;
    },
    staleTime: 60_000,
    retry: false,
  });
}

export function ConsentGate() {
  const t = useT();
  const qc = useQueryClient();
  const consent = useConsent();
  const accept = useMutation({
    mutationFn: async (version: string) => {
      const { data, error } = await api.POST("/me/consent", { body: { version } });
      if (error !== undefined || !data) throw error ?? new Error("consent");
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["consent"] }),
    onError: () => toast(t("Saqlanmadi, qaytadan urinib ko'ring"), "crit"),
  });
  const c = consent.data;
  if (!c || c.accepted) return null;
  const decline = () => api.POST("/auth/logout").finally(() => (location.href = "/login"));
  return (
    <Modal
      title={t("Ma'lumotlarni qayta ishlashga rozilik")}
      onClose={() => undefined /* без согласия кабинетом пользоваться нельзя */}
      footer={
        <>
          <Button variant="ghost" onClick={decline}>{t("Rad etish va chiqish")}</Button>
          <Button onClick={() => accept.mutate(c.version)} disabled={accept.isPending}>{t("Roziman")}</Button>
        </>
      }
    >
      <p>{t("Xizmat ishlashi uchun quyidagilarga ruxsatingiz kerak:")}</p>
      <ul style={{ margin: "8px 0 8px 18px" }}>
        {c.scopes.map((s) => <li key={s}>{t(SCOPE_TEXT[s] ?? s)}</li>)}
      </ul>
      <p className="note">
        {t("Rozilikni istalgan vaqtda qaytarib olishingiz mumkin: «Ma'lumotlarimni o'chirish» shifrlash kalitini o'chiradi va saqlangan ma'lumotlar o'qib bo'lmaydigan bo'ladi.")}
      </p>
    </Modal>
  );
}

export function DeleteMyData() {
  const t = useT();
  const [open, setOpen] = useState(false);
  const del = useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/me/data");
      if (error !== undefined && response.status !== 204) throw error;
    },
    onSuccess: () => (location.href = "/login"),
    onError: () => toast(t("O'chirib bo'lmadi, qaytadan urinib ko'ring"), "crit"),
  });
  return (
    <div style={{ textAlign: "center", margin: "24px 0 0" }}>
      <button type="button" className="link" onClick={() => setOpen(true)}>{t("Ma'lumotlarimni o'chirish")}</button>
      {open ? (
        <Modal
          title={t("Ma'lumotlaringiz o'chirilsinmi?")}
          onClose={() => setOpen(false)}
          footer={
            <>
              <Button variant="ghost" onClick={() => setOpen(false)}>{t("Bekor qilish")}</Button>
              <Button onClick={() => del.mutate()} disabled={del.isPending}>{t("Ha, o'chirish")}</Button>
            </>
          }
        >
          <p>{t("Shifrlash kalitingiz o'chiriladi: kabinet sessiyalari, hujjatlarning asl ma'lumotlari, Telegram va skrinshotlar o'qib bo'lmaydigan bo'ladi. Barcha qurilmalardan chiqasiz. Buni qaytarib bo'lmaydi.")}</p>
        </Modal>
      ) : null}
    </div>
  );
}
