"use client";

import { useState } from "react";

import { Badge, Button, Card, EmptyState, Icon, PageHeader, Skeleton, toast } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";

import { SCOPE, fmtDateTime } from "./labels";
import { useAcceptInvite, useFamily, useInvite, useRevokeConsent } from "./queries";

// UC-G7 / FR-G-13: владелец делится лентой с родственником по коду (read_documents и/или receive_alerts),
// родственник видит ленту только для чтения; отзыв действует сразу. G7 копирует critical-тревоги.
const ALL_SCOPES: Schemas["ConsentScope"][] = ["read_documents", "receive_alerts"];

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
}

export function FamilyPage() {
  const family = useFamily();
  const iShare = family.data?.i_share_with ?? [];
  const sharedWithMe = family.data?.shared_with_me ?? [];

  return (
    <>
      <PageHeader title="Oila" subtitle="Ma'lumotlaringizni kim ko'ra oladi va siz kimning ma'lumotini ko'rasiz" />

      <div className="family-grid">
        <InviteCard />
        <AcceptCard />
      </div>

      <Card title="Men ulashganlar" icon="family">
        {family.isLoading ? (
          <Skeleton rows={2} />
        ) : iShare.length === 0 ? (
          <EmptyState title="Hali hech kimga ulashmagansiz" hint="Yuqoridagi kod orqali qarindoshingizni taklif qiling" />
        ) : (
          <div className="consent-list">
            {iShare.map((c) => <ConsentRow key={c.id} consent={c} mine />)}
          </div>
        )}
      </Card>

      <Card title="Menga ulashilgan" icon="shield2">
        {family.isLoading ? (
          <Skeleton rows={1} />
        ) : sharedWithMe.length === 0 ? (
          <EmptyState title="Sizga hech kim ulashmagan" hint="Qarindoshingiz bergan kodni yuqorida kiriting" />
        ) : (
          <div className="consent-list">
            {sharedWithMe.map((c) => <ConsentRow key={c.id} consent={c} mine={false} />)}
          </div>
        )}
      </Card>
    </>
  );
}

function InviteCard() {
  const invite = useInvite();
  const [scopes, setScopes] = useState<Schemas["ConsentScope"][]>(["receive_alerts"]);
  const [code, setCode] = useState<string | null>(null);

  const toggle = (s: Schemas["ConsentScope"]) =>
    setScopes((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const make = () =>
    invite.mutate(scopes, {
      onSuccess: (r) => { setCode(r.code); toast("Taklif kodi yaratildi", "good"); },
      onError: () => toast("Kodni yaratib bo'lmadi", "crit"),
    });

  const copy = () => code && navigator.clipboard?.writeText(code).then(() => toast("Nusxalandi", "info")).catch(() => {});

  return (
    <Card title="Qarindoshni taklif qilish" icon="family">
      <div className="note" style={{ marginBottom: 12 }}>Qanday huquq berasiz:</div>
      <div className="scope-list">
        {ALL_SCOPES.map((s) => (
          <label key={s} className={`scope${scopes.includes(s) ? " on" : ""}`}>
            <input type="checkbox" checked={scopes.includes(s)} onChange={() => toggle(s)} />
            <div><b>{SCOPE[s].label}</b><small>{SCOPE[s].hint}</small></div>
          </label>
        ))}
      </div>
      {code ? (
        <div className="code-box">
          <span className="tnum">{code}</span>
          <Button variant="ghost" small onClick={copy}><Icon name="file2" size={16} /> Nusxalash</Button>
        </div>
      ) : (
        <Button onClick={make} disabled={scopes.length === 0 || invite.isPending} className="full">
          {invite.isPending ? "…" : "Taklif kodini olish"}
        </Button>
      )}
    </Card>
  );
}

function AcceptCard() {
  const accept = useAcceptInvite();
  const [code, setCode] = useState("");
  const submit = () =>
    accept.mutate(code.trim(), {
      onSuccess: () => { setCode(""); toast("Ulanildi", "good"); },
      onError: () => toast("Kod noto'g'ri yoki muddati o'tgan", "crit"),
    });

  return (
    <Card title="Taklif kodini kiritish" icon="shield2">
      <div className="note" style={{ marginBottom: 12 }}>Qarindoshingiz bergan kodni kiriting — uning lentasini ko&apos;rishni boshlaysiz.</div>
      <input className="code-in wide" value={code} onChange={(e) => setCode(e.target.value)}
        placeholder="Taklif kodi" onKeyDown={(e) => e.key === "Enter" && submit()} aria-label="Taklif kodi" />
      <Button onClick={submit} disabled={!code.trim() || accept.isPending} className="full" style={{ marginTop: 12 }}>
        {accept.isPending ? "…" : "Qabul qilish"}
      </Button>
    </Card>
  );
}

function ConsentRow({ consent, mine }: { consent: Schemas["Consent"]; mine: boolean }) {
  const revoke = useRevokeConsent();
  const person = mine ? consent.grantee : consent.grantor;
  return (
    <div className="consent">
      <div className="avatar sm">{initials(person.display_name)}</div>
      <div className="dmain">
        <div className="dtitle">{person.display_name}</div>
        <div className="dmeta">
          {consent.scopes.map((s) => <Badge key={s} tone="info">{SCOPE[s].label}</Badge>)}
          <span>{fmtDateTime(consent.granted_at)}</span>
        </div>
      </div>
      {mine ? (
        <Button variant="ghost" small disabled={revoke.isPending}
          onClick={() => revoke.mutate(consent.id, {
            onSuccess: () => toast("Ruxsat bekor qilindi", "info"),
            onError: () => toast("Bekor qilib bo'lmadi", "crit"),
          })}>
          <Icon name="x" size={16} /> Bekor qilish
        </Button>
      ) : (
        <Badge tone="good">Faol</Badge>
      )}
    </div>
  );
}
