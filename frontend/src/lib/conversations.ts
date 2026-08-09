import type { EvidenceChunk } from "../api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: EvidenceChunk[];
  dropped?: string[];
  unanswerable?: boolean;
  feedback?: "up" | "down";
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  project: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

const KEY = "veritasiq_conversations";
const MAX_CONVERSATIONS = 50;

export function uid(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

export function loadConversations(): Conversation[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || "[]") as Conversation[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persist(list: Conversation[]): void {
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX_CONVERSATIONS)));
}

export function saveConversation(conv: Conversation): Conversation[] {
  const list = loadConversations();
  const idx = list.findIndex((c) => c.id === conv.id);
  if (idx >= 0) list[idx] = conv;
  else list.unshift(conv);
  persist(list);
  return list;
}

export function deleteConversation(id: string): Conversation[] {
  persist(loadConversations().filter((c) => c.id !== id));
  return loadConversations();
}

export function clearConversations(): Conversation[] {
  persist([]);
  return [];
}

export function dayGroup(date: string): "Today" | "Yesterday" | "Previous 7 days" | "Older" {
  const now = new Date();
  const then = new Date(date);
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfDay = new Date(then.getFullYear(), then.getMonth(), then.getDate()).getTime();
  const diffDays = Math.round((startOfToday - startOfDay) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return "Previous 7 days";
  return "Older";
}
