"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Badge, Card, EmptyState, PageHeader } from "@/components/mygov";
import { api } from "@/lib/api/client";

// Разработчик 1: вкладки по типу, фильтр по статусу, поиск, метка «новое», обновление по SSE (useStream).
export function DocumentFeed() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const { data, error } = await api.GET("/documents", {});
      if (error) throw error;
      return data;
    },
  });

  return (
    <>
      <PageHeader title="Hujjatlarim" subtitle="Все документы на ваше имя из госреестров" />
      <Card>
        {isLoading ? <p className="text-sm text-muted">Загрузка…</p> : null}
        {error ? <EmptyState title="API ещё не готов" hint="Запустите Prism-мок: make mock" /> : null}
        <ul className="divide-y divide-border">
          {data?.items.map((d) => (
            <li key={d.id} className="flex items-center justify-between py-3">
              <Link href={`/documents/${d.id}`} className="font-medium hover:underline">
                {d.title}
              </Link>
              <Badge tone={d.status === "active" ? "good" : "muted"}>{d.status}</Badge>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}
