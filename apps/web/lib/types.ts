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

export type FileProcessingStatus = "queued" | "processing" | "done" | "error" | "unsupported";

export interface FileOut {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  status: FileProcessingStatus;
  error: string | null;
  created_at: string;
}

export type SuggestionStatus = "pending" | "accepted" | "rejected";

export interface TaskSuggestionOut {
  id: string;
  file_id: string | null;
  title: string;
  due_date: string | null;
  priority: 1 | 2 | 3;
  person: string | null;
  quote: string;
  status: SuggestionStatus;
  dedup_of_task_id: string | null;
  created_at: string;
}

export type CalendarKind = "ics" | "caldav" | "google";

export interface CalendarAccountOut {
  id: string;
  kind: CalendarKind;
  name: string;
  url: string | null;
  username: string | null;
  enabled: boolean;
  last_synced_at: string | null;
}

export interface CalendarEventOut {
  id: string;
  uid: string;
  title: string;
  start_at: string;
  end_at: string | null;
  description: string | null;
  location: string | null;
}

export type SearchResultType = "task" | "file" | "event" | "person";

export interface SearchResultOut {
  type: SearchResultType;
  id: string;
  title: string;
  subtitle: string | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResultOut[];
}
