import React, { useState } from "react";
import {
  Copy,
  Trash2,
  ChevronDown,
  ChevronUp,
  Tag,
  MapPin,
  Clock,
} from "lucide-react";

type MemoryCardProps = {
  id: number | string;
  title: string;
  tag: string;
  relevance: number;
  context?: string;
  origin?: string;
  created_at?: string;
  onDelete?: (id: number | string) => void;
  onCopy?: (content: string) => void;
};

export const MemoryCard: React.FC<MemoryCardProps> = ({
  id,
  title,
  tag,
  relevance,
  context,
  origin,
  created_at,
  onDelete,
  onCopy,
}) => {
  const [expanded, setExpanded] = useState(false);

  const hasMetadata = !!(context || origin || created_at);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(title).catch(() => {});
    onCopy?.(title);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(id);
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const relevanceColor =
    relevance >= 80
      ? "text-emerald-400"
      : relevance >= 50
        ? "text-yellow-400"
        : "text-slate-400";

  return (
    <div
      className={`border rounded-lg bg-slate-800/50 transition-all duration-200 ${
        expanded
          ? "border-purple-500/40 bg-slate-800/80"
          : "border-slate-700 hover:border-slate-600 hover:bg-slate-800"
      }`}
    >
      {/* Main row */}
      <div
        className="p-4 cursor-pointer select-none"
        onClick={() => hasMetadata && setExpanded((v) => !v)}
        role={hasMetadata ? "button" : undefined}
        aria-expanded={hasMetadata ? expanded : undefined}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <p className="text-sm font-medium text-white leading-snug flex-1 min-w-0 break-words">
            {title}
          </p>

          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={handleCopy}
              title="Copy content"
              className="p-1.5 hover:bg-slate-700 rounded transition text-slate-500 hover:text-slate-300"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
            {onDelete && (
              <button
                onClick={handleDelete}
                title="Delete memory"
                className="p-1.5 hover:bg-red-900/40 rounded transition text-slate-500 hover:text-red-400"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
            {hasMetadata && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded((v) => !v);
                }}
                title={expanded ? "Collapse details" : "Expand details"}
                className="p-1.5 hover:bg-slate-700 rounded transition text-slate-500 hover:text-purple-400"
              >
                {expanded ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>
        </div>

        {/* Tags / relevance row */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="px-2 py-0.5 text-xs font-semibold bg-purple-900/40 border border-purple-700/60 text-purple-400 rounded">
            {tag}
          </span>
          <span className={`text-xs font-medium ${relevanceColor}`}>
            {relevance}% relevance
          </span>
          {created_at && (
            <span className="text-xs text-slate-500 ml-auto">
              {formatDate(created_at)}
            </span>
          )}
        </div>
      </div>

      {/* Expandable metadata panel */}
      {expanded && hasMetadata && (
        <div className="border-t border-slate-700/60 px-4 py-3 space-y-2.5 bg-slate-900/40 rounded-b-lg">
          {context && (
            <div className="flex gap-2">
              <MapPin className="w-3.5 h-3.5 text-purple-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-0.5">
                  Context
                </p>
                <p className="text-xs text-slate-300 break-words">{context}</p>
              </div>
            </div>
          )}

          {origin && (
            <div className="flex gap-2">
              <Tag className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-0.5">
                  Origin
                </p>
                <p className="text-xs text-slate-300 break-words">{origin}</p>
              </div>
            </div>
          )}

          {created_at && (
            <div className="flex gap-2">
              <Clock className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-0.5">
                  Stored at
                </p>
                <p className="text-xs text-slate-300">
                  {formatDate(created_at)}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
