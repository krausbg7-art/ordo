"use client";

import { useState } from "react";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { StatusOut, TaskOut } from "@/lib/types";
import TaskCard from "./TaskCard";

export default function StatusColumn({
  status,
  tasks,
  onCardClick,
  onRename,
  onAddTask,
}: {
  status: StatusOut;
  tasks: TaskOut[];
  onCardClick: (task: TaskOut) => void;
  onRename: (statusId: string, name: string) => void;
  onAddTask: (statusId: string, title: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status.id });
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(status.name);
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  function commitRename() {
    setEditing(false);
    if (name.trim() && name !== status.name) onRename(status.id, name.trim());
  }

  function commitAdd() {
    if (newTitle.trim()) {
      onAddTask(status.id, newTitle.trim());
      setNewTitle("");
    }
    setAdding(false);
  }

  return (
    <div
      ref={setNodeRef}
      className={`bg-cream border rounded-2xl p-2.5 min-h-[420px] flex flex-col gap-2 min-w-[220px] snap-start ${
        isOver ? "border-[var(--brass)] bg-[#F1EADB]" : "border-[var(--line)]"
      }`}
    >
      <div className="flex justify-between items-center px-1.5 pb-1.5">
        {editing ? (
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => e.key === "Enter" && commitRename()}
            className="serif text-xl font-medium text-[var(--brass-ink)] bg-transparent border-b border-[var(--line2)] outline-none w-full"
          />
        ) : (
          <span
            className="serif text-xl font-medium text-[var(--brass-ink)] cursor-text"
            onClick={() => setEditing(true)}
          >
            {status.name}
          </span>
        )}
        <span className="text-xs text-[var(--stone)] ml-2">{tasks.length}</span>
      </div>

      <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onClick={() => onCardClick(task)} />
          ))}
        </div>
      </SortableContext>

      {adding ? (
        <input
          autoFocus
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onBlur={commitAdd}
          onKeyDown={(e) => e.key === "Enter" && commitAdd()}
          placeholder="Название задачи"
          className="border border-[var(--line2)] rounded-xl px-3 py-2 text-sm bg-white"
        />
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="border border-dashed border-[var(--line2)] rounded-xl min-h-[40px] text-sm text-[var(--stone)]"
        >
          + добавить задачу
        </button>
      )}
    </div>
  );
}
