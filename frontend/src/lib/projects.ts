/** Frontend-only project grouping of documents (stored in localStorage).
 * Projects are a presentation layer concept — no backend changes. */

import type { DocumentItem } from "../api";

const KEY = "veritasiq_projects";

export interface ProjectMapping {
  [documentId: string]: string; // document id -> project name
}

export function loadMapping(): ProjectMapping {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}") as ProjectMapping;
  } catch {
    return {};
  }
}

function saveMapping(mapping: ProjectMapping): void {
  localStorage.setItem(KEY, JSON.stringify(mapping));
}

export function projectFor(documentId: string): string {
  return loadMapping()[documentId] || "Unassigned";
}

export function assignProject(documentId: string, project: string): void {
  const mapping = loadMapping();
  mapping[documentId] = project;
  saveMapping(mapping);
}

export function renameProject(oldName: string, newName: string): void {
  const mapping = loadMapping();
  for (const [id, name] of Object.entries(mapping)) {
    if (name === oldName) mapping[id] = newName;
  }
  saveMapping(mapping);
}

export interface ProjectGroup {
  name: string;
  documents: DocumentItem[];
}

export function groupDocuments(documents: DocumentItem[]): ProjectGroup[] {
  const mapping = loadMapping();
  const groups = new Map<string, DocumentItem[]>();
  for (const doc of documents) {
    const name = mapping[doc.id] || "Unassigned";
    const list = groups.get(name) || [];
    list.push(doc);
    groups.set(name, list);
  }
  return Array.from(groups.entries())
    .map(([name, docs]) => ({ name, documents: docs }))
    .sort((a, b) => (a.name === "Unassigned" ? 1 : b.name === "Unassigned" ? -1 : a.name.localeCompare(b.name)));
}

export function allProjectNames(): string[] {
  const names = new Set<string>(["Unassigned"]);
  for (const name of Object.values(loadMapping())) names.add(name);
  return Array.from(names);
}
