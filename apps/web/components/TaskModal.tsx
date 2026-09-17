"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { TaskOut } from "@/lib/types";

export default function TaskModal({
  task,
  onClose,
  onSaved,
  onDeleted,
}: {
  task: TaskOut;
  onClose: () => void;
  onSaved: (task: TaskOut) => void;
  onDeleted: (taskId: string) => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? "");
  const [priority, setPriority] = useState(task.priority);
  const [dueDate, setDueDate] = useState(task.due_date ?? "");
  const [person, setPerson] = useState(task.person ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const updated = await api.patch<TaskOut>(`/tasks/${task.id}`, {
        title,
        description: description || null,
        priority,
        due_date: dueDate || null,
        person: person || null,
      });
      onSaved(updated);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!confirm("Удалить задачу?")) return;
    await api.delete(`/tasks/${task.id}`);
    onDeleted(task.id);
  }

  return (
    <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 px-4" onClick={onClose}>
      <div
        className="bg-[var(--paper)] rounded-3xl p-6 w-full max-w-md flex flex-col gap-3"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="serif text-3xl mb-1">Задача</h3>

        <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
          Название
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="border border-[var(--line2)] rounded-xl px-3 py-2 bg-white"
          />
        </label>

        <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
          Описание
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="border border-[var(--line2)] rounded-xl px-3 py-2 bg-white"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
            Приоритет
            <select
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value) as 1 | 2 | 3)}
              className="border border-[var(--line2)] rounded-xl px-3 py-2 bg-white"
            >
              <option value={1}>1 — высокий</option>
              <option value={2}>2 — средний</option>
              <option value={3}>3 — низкий</option>
            </select>
          </label>
          <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
            Срок
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="border border-[var(--line2)] rounded-xl px-3 py-2 bg-white"
            />
          </label>
        </div>

        <label className="text-sm text-[var(--stone)] flex flex-col gap-1">
          Человек
          <input
            value={person}
            onChange={(e) => setPerson(e.target.value)}
            className="border border-[var(--line2)] rounded-xl px-3 py-2 bg-white"
          />
        </label>

        <div className="flex justify-between items-center mt-2">
          <button onClick={remove} className="text-sm text-red-700">
            Удалить
          </button>
          <div className="flex gap-2">
            <button onClick={onClose} className="border border-[var(--line2)] rounded-xl px-4 py-2 text-sm">
              Отмена
            </button>
            <button
              onClick={save}
              disabled={saving}
              className="bg-ink text-cream rounded-xl px-4 py-2 text-sm font-semibold disabled:opacity-60"
            >
              Сохранить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
