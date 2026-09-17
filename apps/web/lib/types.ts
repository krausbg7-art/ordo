export type SourceType = "mail" | "calendar" | "file" | "call" | "note" | "manual";
export type CreatedBy = "user" | "ai";

export interface StatusOut {
  id: string;
  name: string;
  order: number;
  color: string;
}

export interface BoardOut {
  id: string;
  name: string;
  statuses: StatusOut[];
}

export interface TaskOut {
  id: string;
  board_id: string;
  status_id: string;
  title: string;
  description: string | null;
  priority: 1 | 2 | 3;
  due_date: string | null;
  person: string | null;
  source_type: SourceType;
  source_ref: string | null;
  position: number;
  created_by: CreatedBy;
  created_at: string;
  updated_at: string;
}

export interface TodayTask {
  task: TaskOut;
  reason: string;
}

export interface UserOut {
  id: string;
  email: string;
}
