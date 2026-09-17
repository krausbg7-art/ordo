"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { SearchResponse, SearchResultOut } from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  task: "задача",
  file: "файл",
  event: "событие",
  person: "человек",
};

const TYPE_ROUTE: Record<string, string> = {
  task: "/board",
  file: "/files",
  event: "/calendars",
  person: "/board",
};

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultOut[]>([]);
  const [open, setOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    timerRef.current = setTimeout(async () => {
      const resp = await api.get<SearchResponse>(`/search?q=${encodeURIComponent(query)}`);
      setResults(resp.results);
      setOpen(true);
    }, 150);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  async function onSelect(result: SearchResultOut) {
    setOpen(false);
    await api.post("/search/click", { query, result_type: result.type, result_id: result.id });
    router.push(TYPE_ROUTE[result.type] ?? "/today");
  }

  return (
    <div className="relative max-w-xl">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Поиск по задачам, файлам, событиям, людям…"
        className="w-full h-13 border border-[var(--line2)] rounded-2xl px-4 py-3 text-base bg-white"
      />
      {open && (
        <div className="absolute z-20 top-full mt-2 w-full bg-white border border-[var(--line)] rounded-2xl shadow-lg max-h-80 overflow-auto">
          {results.length === 0 ? (
            <div className="p-4 text-sm text-[var(--stone)]">Ничего не найдено</div>
          ) : (
            results.map((r) => (
              <button
                key={`${r.type}-${r.id}`}
                onMouseDown={() => onSelect(r)}
                className="w-full text-left flex items-center gap-3 px-4 py-3 border-b border-[var(--line)] last:border-0 hover:bg-[var(--linen)]"
              >
                <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--linen)] whitespace-nowrap">
                  {TYPE_LABEL[r.type] ?? r.type}
                </span>
                <span className="flex-1 min-w-0">
                  <b className="block text-sm font-medium truncate">{r.title}</b>
                  {r.subtitle && <span className="block text-xs text-[var(--stone)] truncate">{r.subtitle}</span>}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
