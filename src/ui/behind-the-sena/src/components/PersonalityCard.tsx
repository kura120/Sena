import React, { useState } from "react";
import {
  Check,
  X,
  Trash2,
  Edit3,
  ChevronDown,
  ChevronUp,
  Sparkles,
  User,
  Tag,
  Clock,
  AlertCircle,
} from "lucide-react";

export type PersonalityFragment = {
  fragment_id: string;
  content: string;
  fragment_type: "explicit" | "inferred";
  category?: string;
  confidence?: number;
  status: "pending" | "approved" | "rejected";
  source?: string;
  created_at?: string;
  approved_at?: string;
  metadata?: Record<string, unknown>;
};

type PersonalityCardProps = {
  fragment: PersonalityFragment;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onDelete?: (id: string) => void;
  onEdit?: (id: string, newContent: string) => void;
  showActions?: boolean;
};

export const PersonalityCard: React.FC<PersonalityCardProps> = ({
  fragment,
  onApprove,
  onReject,
  onDelete,
  onEdit,
  showActions = true,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(fragment.content);
  const [saving, setSaving] = useState(false);

  const isPending = fragment.status === "pending";
  const isApproved = fragment.status === "approved";
  const isRejected = fragment.status === "rejected";
  const isInferred = fragment.fragment_type === "inferred";

  const confidencePct = fragment.confidence != null
    ? Math.round(fragment.confidence * 100)
    : null;

  const confidenceColor =
    confidencePct == null
      ? "text-slate-400"
      : confidencePct >= 85
        ? "text-emerald-400"
        : confidencePct >= 65
          ? "text-yellow-400"
          : "text-red-400";

  const statusBadge = () => {
    if (isPending)
      return (
        <span className="px-2 py-0.5 text-[10px] font-semibold rounded border bg-yellow-500/10 border-yellow-600/50 text-yellow-400 uppercase tracking-wider">
          Pending
        </span>
      );
    if (isApproved)
      return (
        <span className="px-2 py-0.5 text-[10px] font-semibold rounded border bg-emerald-500/10 border-emerald-600/50 text-emerald-400 uppercase tracking-wider">
          Approved
        </span>
      );
    if (isRejected)
      return (
        <span className="px-2 py-0.5 text-[10px] font-semibold rounded border bg-red-500/10 border-red-600/50 text-red-400 uppercase tracking-wider">
          Rejected
        </span>
      );
    return null;
  };

  const typeBadge = () => {
    if (isInferred)
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold rounded border bg-purple-500/10 border-purple-700/50 text-purple-400 uppercase tracking-wider">
          <Sparkles className="w-2.5 h-2.5" />
          Inferred
        </span>
      );
    return (
      <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold rounded border bg-cyan-500/10 border-cyan-700/50 text-cyan-400 uppercase tracking-wider">
        <User className="w-2.5 h-2.5" />
        Explicit
      </span>
    );
  };

  const formatDate = (iso?: string) => {
    if (!iso) return null;
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

  const handleSaveEdit = async () => {
    if (!editValue.trim() || editValue === fragment.content) {
      setEditing(false);
      setEditValue(fragment.content);
      return;
    }
    setSaving(true);
    try {
      await onEdit?.(fragment.fragment_id, editValue.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setEditValue(fragment.content);
  };

  const borderColor = isPending
    ? "border-yellow-700/40 hover:border-yellow-600/60"
    : isApproved
      ? "border-emerald-700/30 hover:border-emerald-600/50"
      : "border-slate-700/60 hover:border-slate-600";

  const hasDetails = !!(fragment.source || fragment.created_at || fragment.approved_at || fragment.category);

  return (
    <div
      className={`border rounded-lg bg-slate-800/50 transition-all duration-200 ${borderColor} ${
        expanded ? "bg-slate-800/80" : ""
      }`}
    >
      {/* Main content */}
      <div className="p-4">
        {/* Header row: badges + actions */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {typeBadge()}
            {statusBadge()}
            {fragment.category && (
              <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] rounded border bg-slate-700/40 border-slate-600/50 text-slate-400 uppercase tracking-wider">
                <Tag className="w-2.5 h-2.5" />
                {fragment.category}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {/* Expand/collapse details */}
            {hasDetails && (
              <button
                onClick={() => setExpanded((v) => !v)}
                title={expanded ? "Collapse" : "Expand details"}
                className="p-1.5 hover:bg-slate-700 rounded transition text-slate-500 hover:text-purple-400"
              >
                {expanded ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            )}

            {/* Edit */}
            {showActions && !editing && !isRejected && (
              <button
                onClick={() => setEditing(true)}
                title="Edit fragment"
                className="p-1.5 hover:bg-slate-700 rounded transition text-slate-500 hover:text-blue-400"
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Delete */}
            {showActions && onDelete && (
              <button
                onClick={() => onDelete(fragment.fragment_id)}
                title="Delete fragment"
                className="p-1.5 hover:bg-red-900/40 rounded transition text-slate-500 hover:text-red-400"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Content / edit area */}
        {editing ? (
          <div className="space-y-2">
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              rows={3}
              className="w-full bg-slate-900 border border-slate-600 focus:border-purple-500 rounded px-3 py-2 text-sm text-slate-100 resize-none outline-none transition"
              autoFocus
              disabled={saving}
            />
            <div className="flex items-center gap-2">
              <button
                onClick={handleSaveEdit}
                disabled={saving || !editValue.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded transition"
              >
                <Check className="w-3 h-3" />
                {saving ? "Saving…" : "Save & Approve"}
              </button>
              <button
                onClick={handleCancelEdit}
                disabled={saving}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition"
              >
                <X className="w-3 h-3" />
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-200 leading-snug break-words">
            {fragment.content}
          </p>
        )}

        {/* Bottom row: confidence + approve/reject actions */}
        {!editing && (
          <div className="flex items-center justify-between gap-3 mt-3 flex-wrap">
            {/* Confidence score (inferred only) */}
            {isInferred && confidencePct != null && (
              <div className="flex items-center gap-1.5">
                {confidencePct < 70 && (
                  <AlertCircle className="w-3 h-3 text-yellow-500" />
                )}
                <span className={`text-xs font-medium ${confidenceColor}`}>
                  {confidencePct}% confidence
                </span>
              </div>
            )}

            {/* Approve / Reject buttons (pending only) */}
            {showActions && isPending && (
              <div className="flex items-center gap-2 ml-auto">
                {onReject && (
                  <button
                    onClick={() => onReject(fragment.fragment_id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-900/30 hover:bg-red-900/60 border border-red-700/50 text-red-400 hover:text-red-300 rounded transition"
                  >
                    <X className="w-3 h-3" />
                    Reject
                  </button>
                )}
                {onApprove && (
                  <button
                    onClick={() => onApprove(fragment.fragment_id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-900/30 hover:bg-emerald-900/60 border border-emerald-700/50 text-emerald-400 hover:text-emerald-300 rounded transition"
                  >
                    <Check className="w-3 h-3" />
                    Approve
                  </button>
                )}
              </div>
            )}

            {/* Approved timestamp */}
            {isApproved && fragment.approved_at && (
              <span className="text-[10px] text-slate-500 ml-auto">
                Approved {formatDate(fragment.approved_at)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Expandable details panel */}
      {expanded && hasDetails && (
        <div className="border-t border-slate-700/60 px-4 py-3 space-y-2 bg-slate-900/40 rounded-b-lg">
          {fragment.source && (
            <div className="flex gap-2 items-start">
              <Tag className="w-3.5 h-3.5 text-purple-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-0.5">Source</p>
                <p className="text-xs text-slate-300 break-words">{fragment.source}</p>
              </div>
            </div>
          )}
          {fragment.created_at && (
            <div className="flex gap-2 items-start">
              <Clock className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-0.5">Created</p>
                <p className="text-xs text-slate-300">{formatDate(fragment.created_at)}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
