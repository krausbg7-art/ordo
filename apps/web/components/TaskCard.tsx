"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { TaskOut } from "@/lib/types";

const PRIORITY_DOT: Record<number, string> = {
  1: "bg-[#9A3B2E]",
  2: "bg-[var(--brass)]",
  3: "bg-[#9C978C]",
};

const SOURCE_LABEL: Record<string, string> = {
  mail: "почта",
  calendar: "календарь",
  file: "файл",
  call: "звонок",
  note: "заметка",
  manual: "вручную",
};

export default function TaskCard({ task, onClick }: { task: TaskOut; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
  };

  return (
    <button
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className="bg-white border border-[var(--line)] rounded-2xl p-3 text-left flex flex-col gap-2 cursor-grab active:cursor-grabbing w-full"
    >
      <span className="text-sm font-semibold leading-snug">{task.title}</span>
      <span className="flex items-center gap-2 flex-wrap text-xs text-[var(--stone)]">
        <span className={`w-2 h-2 rounded-full inline-block ${PRIORITY_DOT[task.priority]}`} />
        {task.due_date && <span>{task.due_date}</span>}
        {task.person && <span>· {task.person}</span>}
        <span className="text-[11px] px-2 py-0.5 rounded-full bg-[var(--linen)]">
          {SOURCE_LABEL[task.source_type] ?? task.source_type}
        </span>
      </span>
    </button>
  );
}
