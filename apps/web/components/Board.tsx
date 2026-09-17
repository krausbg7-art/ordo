"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { api } from "@/lib/api";
import type { BoardOut, StatusOut, TaskOut } from "@/lib/types";
import StatusColumn from "./StatusColumn";
import TaskCard from "./TaskCard";
import TaskModal from "./TaskModal";

export default function Board() {
  const [board, setBoard] = useState<BoardOut | null>(null);
  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [activeTask, setActiveTask] = useState<TaskOut | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskOut | null>(null);
  const [loading, setLoading] = useState(true);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    const boards = await api.get<BoardOut[]>("/boards");
    const b = boards[0];
    setBoard(b);
    const t = await api.get<TaskOut[]>(`/tasks?board_id=${b.id}`);
    setTasks(t);
    setLoading(false);
  }

  const tasksByStatus = useMemo(() => {
    const grouped: Record<string, TaskOut[]> = {};
    for (const status of board?.statuses ?? []) grouped[status.id] = [];
    for (const task of tasks) {
      if (!grouped[task.status_id]) grouped[task.status_id] = [];
      grouped[task.status_id].push(task);
    }
    for (const key of Object.keys(grouped)) grouped[key].sort((a, b) => a.position - b.position);
    return grouped;
  }, [board, tasks]);

  function findStatusIdForTask(taskId: string): string | undefined {
    return tasks.find((t) => t.id === taskId)?.status_id;
  }

  function onDragStart(event: DragStartEvent) {
    const task = tasks.find((t) => t.id === event.active.id);
    setActiveTask(task ?? null);
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveTask(null);
    if (!over) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    const sourceStatusId = findStatusIdForTask(activeId);
    const isOverColumn = board?.statuses.some((s) => s.id === overId);
    const targetStatusId = isOverColumn ? overId : findStatusIdForTask(overId);
    if (!sourceStatusId || !targetStatusId) return;

    const targetList = tasksByStatus[targetStatusId] ?? [];
    let targetIndex = isOverColumn ? targetList.length : targetList.findIndex((t) => t.id === overId);
    if (targetIndex < 0) targetIndex = targetList.length;
    if (sourceStatusId === targetStatusId) {
      const currentIndex = targetList.findIndex((t) => t.id === activeId);
      if (currentIndex === targetIndex) return;
    }

    // Оптимистичное обновление
    setTasks((prev) => {
      const withoutActive = prev.filter((t) => t.id !== activeId);
      const moved = prev.find((t) => t.id === activeId);
      if (!moved) return prev;
      const updated = { ...moved, status_id: targetStatusId };
      const listForTarget = withoutActive.filter((t) => t.status_id === targetStatusId).sort((a, b) => a.position - b.position);
      listForTarget.splice(targetIndex, 0, updated);
      const rest = withoutActive.filter((t) => t.status_id !== targetStatusId);
      return [...rest, ...listForTarget.map((t, i) => ({ ...t, position: i }))];
    });

    try {
      await api.post(`/tasks/${activeId}/move`, { status_id: targetStatusId, position: targetIndex });
    } catch {
      await load();
    }
  }

  async function renameStatus(statusId: string, name: string) {
    await api.patch(`/statuses/${statusId}`, { name });
    setBoard((prev) =>
      prev ? { ...prev, statuses: prev.statuses.map((s) => (s.id === statusId ? { ...s, name } : s)) } : prev
    );
  }

  async function addTask(statusId: string, title: string) {
    const created = await api.post<TaskOut>("/tasks", { title, status_id: statusId, board_id: board?.id });
    setTasks((prev) => [...prev, created]);
  }

  async function addStatus() {
    if (!board) return;
    const name = prompt("Название нового статуса");
    if (!name) return;
    const created = await api.post<StatusOut>(`/boards/${board.id}/statuses`, { name });
    setBoard((prev) => (prev ? { ...prev, statuses: [...prev.statuses, created] } : prev));
  }

  async function onTaskSaved(updated: TaskOut) {
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    setSelectedTask(null);
  }

  async function onTaskDeleted(taskId: string) {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    setSelectedTask(null);
  }

  if (loading || !board) return <p className="text-[var(--stone)]">Загрузка доски…</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="serif text-4xl">{board.name}</h1>
        <button
          onClick={addStatus}
          className="border border-[var(--line2)] rounded-xl px-4 py-2 text-sm font-semibold bg-white"
        >
          + статус
        </button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={onDragStart} onDragEnd={onDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-2 snap-x">
          {board.statuses
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((status) => (
              <div key={status.id} className="flex-1 basis-[240px]">
                <StatusColumn
                  status={status}
                  tasks={tasksByStatus[status.id] ?? []}
                  onCardClick={setSelectedTask}
                  onRename={renameStatus}
                  onAddTask={addTask}
                />
              </div>
            ))}
        </div>
        <DragOverlay>{activeTask ? <TaskCard task={activeTask} onClick={() => {}} /> : null}</DragOverlay>
      </DndContext>

      {selectedTask && (
        <TaskModal task={selectedTask} onClose={() => setSelectedTask(null)} onSaved={onTaskSaved} onDeleted={onTaskDeleted} />
      )}
    </div>
  );
}
