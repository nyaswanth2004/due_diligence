import type { ComponentType } from "react";
import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  FolderKanban,
  UploadCloud,
  MessagesSquare,
  ShieldAlert,
  FileText,
  Users,
  ScrollText,
  X,
  Sparkles,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useAuth } from "../../context/AuthContext";
import { isAdmin } from "../../auth";

const NAV_SECTIONS: {
  label: string;
  adminOnly?: boolean;
  items: { to: string; label: string; icon: ComponentType<{ className?: string }>; match?: boolean }[];
}[] = [
  {
    label: "Workspace",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard, match: true },
      { to: "/projects", label: "Projects", icon: FolderKanban },
      { to: "/documents", label: "Document Upload", icon: UploadCloud },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/chat", label: "AI Chat", icon: MessagesSquare },
      { to: "/risk", label: "Risk Analysis", icon: ShieldAlert },
      { to: "/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    label: "Administration",
    adminOnly: true,
    items: [
      { to: "/users", label: "Users", icon: Users },
      { to: "/audit", label: "Audit Logs", icon: ScrollText },
    ],
  },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user } = useAuth();
  const admin = isAdmin();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden animate-fade-in"
          onClick={onClose}
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-white/8 bg-surface/98 transition-transform duration-200 ease-out lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-[240px]"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-white/8 px-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-emerald-500 shadow-lg shadow-primary/30">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold leading-tight text-foreground">
                Veritas<span className="text-primary">IQ</span>
              </div>
              <div className="text-[10px] uppercase tracking-widest text-muted">
                Due Diligence
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted hover:bg-white/10 hover:text-foreground lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-5 scroll-thin">
          {NAV_SECTIONS.map((section) => {
            if (section.adminOnly && !admin) return null;
            return (
              <div key={section.label}>
                <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted/60">
                  {section.label}
                </div>
                <div className="space-y-0.5">
                  {section.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.match}
                      onClick={onClose}
                      className={({ isActive }) =>
                        cn(
                          "group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                          isActive
                            ? "bg-primary-soft text-primary"
                            : "text-muted hover:bg-white/5 hover:text-foreground"
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <item.icon
                            className={cn(
                              "h-4 w-4",
                              isActive ? "text-primary" : "text-muted group-hover:text-foreground"
                            )}
                          />
                          <span>{item.label}</span>
                          {isActive && (
                            <motion.span
                              layoutId="sidebar-active"
                              className="ml-auto h-1.5 w-1.5 rounded-full bg-primary"
                            />
                          )}
                        </>
                      )}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="border-t border-white/8 p-3">
          <div className="flex items-center gap-3 rounded-lg bg-white/[0.03] p-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-emerald-500 text-xs font-semibold text-white">
              {(user?.username || "?").slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-semibold text-foreground">
                {user?.username}
              </div>
              <div className="truncate text-[10px] capitalize text-muted">{user?.role}</div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
