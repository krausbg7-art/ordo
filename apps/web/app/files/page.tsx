"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import FileDropzone from "@/components/FileDropzone";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import type { FileOut, FileProcessingStatus, TaskSuggestionOut } from "@/lib/types";

const STATUS_LABEL: Record<FileProcessingStatus, string> = {
  queued: "в очереди",
  processing: "разбирается",
  done: "готово",
  error: "ошибка",
  unsupported: "не поддерживается",
};

const STATUS_COLOR: Record<FileProcessingStatus, string> = {
  queued: "bg-[var(--linen)] text-[var(--soft)]",
  processing: "bg-[#EAE0C8] text-[var(--brass-ink)]",
  done: "bg-[#DCEBDF] text-[#2F5B3C]",
  error: "bg-[#F3D9D4] text-[#8A2F22]",
  unsupported: "bg-[#E4E0EA] text-[#433E52]",
};

export default function FilesPage() {
  const { user, loading } = useAuth();
  const [files, setFiles] = useState<FileOut[]>([]);
  const [suggestions, setSuggestions] = useState<TaskSuggestionOut[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const [filesResp, suggestionsResp] = await Promise.all([
      api.get<FileOut[]>("/files"),
      api.get<TaskSuggestionOut[]>("/suggestions"),
    ]);
    setFiles(filesResp);
    setSuggestions(suggestionsResp);
  }, []);

  useEffect(() => {
    if (!user) return;
    refresh();
  }, [user, refresh]);

  useEffect(() => {
    const hasActive = files.some((f) => f.status === "queued" || f.status === "processing");
    if (hasActive && !pollRef.current) {
      pollRef.current = setInterval(refresh, 2000);
    }
    if (!hasActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [files, refresh]);

  async function onFiles(picked: File[]) {
    setError(null);
    setUploading(true);
    try {
      await api.upload("/files", picked);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить файлы");
    } finally {
      setUploading(false);
    }
  }

  async function accept(id: string) {
    await api.post(`/suggestions/${id}/accept`);
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }

  async function reject(id: string) {
    await api.post(`/suggestions/${id}/reject`);
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }

  if (loading || !user) return null;

  return (
    <AppShell>
      <h1 className="serif text-4xl mb-4">Файлы</h1>

      <FileDropzone onFiles={onFiles} />
      {uploading && <p className="text-sm text-[var(--stone)] mt-2">Загрузка…</p>}
      {error && <p className="text-sm text-red-700 mt-2">{error}</p>}

      <h2 className="serif text-2xl mt-8 mb-3">Загруженные файлы</h2>
      {files.length === 0 ? (
        <p className="text-[var(--stone)]">Файлов пока нет.</p>
      ) : (
        <div className="flex flex-col divide-y divide-[var(--line)] max-w-2xl">
          {files.map((file) => (
            <div key={file.id} className="flex items-center gap-3 py-3">
              <span className="flex-1 min-w-0 truncate text-sm font-medium">{file.filename}</span>
              <span className={`text-xs px-2 py-1 rounded-full whitespace-nowrap ${STATUS_COLOR[file.status]}`}>
                {STATUS_LABEL[file.status]}
              </span>
              {file.error && <span className="text-xs text-red-700">{file.error}</span>}
            </div>
          ))}
        </div>
      )}

      <h2 className="serif text-2xl mt-8 mb-3">Предложенные задачи</h2>
      {suggestions.length === 0 ? (
        <p className="text-[var(--stone)]">Пока нет предложений — загрузите файл, чтобы ИИ нашёл в нём задачи.</p>
      ) : (
        <div className="flex flex-col gap-2 max-w-2xl">
          {suggestions.map((s) => (
            <div key={s.id} className="flex gap-3 items-start bg-white border border-[var(--line)] rounded-2xl p-3">
              <input type="checkbox" className="mt-1 w-5 h-5 accent-ink" onChange={(e) => e.target.checked && accept(s.id)} />
              <div className="flex-1 min-w-0">
                <b className="block text-sm font-semibold">{s.title}</b>
                <span className="text-xs text-[var(--stone)] block">«{s.quote}»</span>
                <span className="text-xs text-[var(--stone)]">
                  {s.due_date && `срок: ${s.due_date} · `}
                  {s.person && `${s.person} · `}
                  приоритет {s.priority}
                  {s.dedup_of_task_id && " · возможно, уже есть"}
                </span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => accept(s.id)} className="text-xs bg-ink text-cream rounded-lg px-3 py-1.5">
                  Добавить на доску
                </button>
                <button onClick={() => reject(s.id)} className="text-xs border border-[var(--line2)] rounded-lg px-3 py-1.5">
                  Отклонить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
