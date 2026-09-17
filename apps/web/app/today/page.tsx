"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import SearchBar from "@/components/SearchBar";
import { useAuth } from "@/lib/useAuth";
import { api } from "@/lib/api";
import type { TodayTask } from "@/lib/types";

const PRIORITY_DOT: Record<number, string> = {
  1: "bg-[#9A3B2E]",
  2: "bg-[var(--brass)]",
  3: "bg-[#9C978C]",
};

export default function TodayPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<TodayTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    api
      .get<TodayTask[]>("/today")
      .then(setItems)
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading || !user) return null;

  return (
    <AppShell>
      <div className="mb-8">
        <SearchBar />
      </div>

      <h1 className="serif text-4xl mb-1">Сегодня</h1>
      <p className="text-[var(--stone)] mb-8">
        {new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
      </p>

      {loading && <p className="text-[var(--stone)]">Загрузка…</p>}

      {!loading && items.length === 0 && (
        <div className="border border-dashed border-[var(--line2)] rounded-2xl p-8 text-center text-[var(--stone)]">
          Главных дел на сегодня нет — можно выдохнуть.
        </div>
      )}

      <div className="flex flex-col gap-3 max-w-2xl">
        {items.map(({ task, reason }, index) => (
          <div key={task.id} className="flex gap-4 bg-white border border-[var(--line)] rounded-2xl p-4">
            <div className="serif text-3xl text-[var(--brass-ink)] w-6">{index + 1}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${PRIORITY_DOT[task.priority]}`} />
                <b className="text-base">{task.title}</b>
              </div>
              <span className="text-sm text-[var(--soft)]">{reason}</span>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
