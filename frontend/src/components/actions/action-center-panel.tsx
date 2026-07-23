"use client";

import { useMemo, useState } from "react";
import type { ButtonHTMLAttributes } from "react";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronRight,
  Plus,
  Save,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  createTrackerFromAction,
  deleteActionItem,
  removeActionProductGroup,
  reorderActionItems,
  reorderActionProductGroups,
  updateActionProductGroupNote,
  updateActionStatus,
  updateActionSuggestions,
} from "@/lib/api/browser";
import type { ActionItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type ActionCenterPanelProps = {
  items: ActionItem[];
};

type ActionDisplayStatus = "in_progress" | "pending_review" | "done";
type ActionFilter = "all" | ActionDisplayStatus;
type StatusOperation = "in_progress" | "enter_review" | "done";

type ProductGroup = {
  key: string;
  name: string;
  note: string;
  sortOrder: number | null;
  actions: ActionItem[];
};

type ConfirmTarget =
  | { type: "product"; group: ProductGroup }
  | { type: "action"; action: ActionItem };

const FILTER_OPTIONS: Array<{ value: ActionFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "in_progress", label: "处理中" },
  { value: "pending_review", label: "复盘中" },
  { value: "done", label: "已完结" },
];

const STATUS_LABELS: Record<ActionDisplayStatus, string> = {
  in_progress: "处理中",
  pending_review: "复盘中",
  done: "已完结",
};

const STATUS_BADGE_CLASS: Record<ActionDisplayStatus, string> = {
  in_progress: "border-[#b8d8ff] bg-[#f2f8ff] text-[#386ea9]",
  pending_review: "border-[#f5d18f] bg-[#fff8e7] text-[#976b14]",
  done: "border-[#bfe6d8] bg-[#f3fffa] text-[#327b64]",
};

const STATUS_OPERATIONS: Array<{ value: StatusOperation; label: string }> = [
  { value: "in_progress", label: "标记处理中" },
  { value: "enter_review", label: "已落实，进入复盘" },
  { value: "done", label: "标记已完结" },
];

export function ActionCenterPanel({ items }: ActionCenterPanelProps) {
  const initialItems = useMemo(() => items.map(normalizeActionItem), [items]);
  const initialGroupKey = initialItems[0] ? getProductGroupKey(initialItems[0]) : null;

  const [actions, setActions] = useState<ActionItem[]>(initialItems);
  const [activeStatus, setActiveStatus] = useState<ActionFilter>("all");
  const [expandedProductKeys, setExpandedProductKeys] = useState<Set<string>>(
    () => new Set(initialGroupKey ? [initialGroupKey] : []),
  );
  const [expandedActionIds, setExpandedActionIds] = useState<Set<number>>(
    () => new Set(initialItems[0] ? [initialItems[0].id] : []),
  );
  const [selectedProductKey, setSelectedProductKey] = useState<string | null>(initialGroupKey);
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>(() => buildInitialNoteDrafts(initialItems));
  const [suggestionDrafts, setSuggestionDrafts] = useState<Record<number, string[]>>(
    () => buildInitialSuggestionDrafts(initialItems),
  );
  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const groups = useMemo(() => {
    const filteredActions =
      activeStatus === "all"
        ? actions
        : actions.filter((action) => normalizeStatus(action.status) === activeStatus);
    return buildProductGroups(filteredActions);
  }, [activeStatus, actions]);

  async function handleStatusOperation(action: ActionItem, operation: StatusOperation): Promise<void> {
    const requestKey = `status-${action.id}`;
    setError("");
    setMessage("");
    setBusyKey(requestKey);
    try {
      if (operation === "enter_review") {
        const response = await createTrackerFromAction(action.id, {
          actionItemId: action.id,
          productId: action.product_id ?? null,
          variantId: action.variant_id ?? null,
          trackerTitle: `${action.tag_name || action.title} 复盘`,
          tagName: action.tag_name ?? null,
          baselinePct: action.current_pct ?? null,
          improvementAction: getPrimarySuggestion(action),
          effectiveBatch: action.expected_effect_batch ?? null,
          reviewScope: action.expected_review_at ?? null,
          currentPct: null,
          resultStatus: "pending",
          conclusion: null,
        });
        replaceAction(response.action);
        setExpandedActionIds((current) => addToSet(current, action.id));
        setMessage("已落实，行动已进入复盘中。");
      } else {
        const updated = await updateActionStatus(action.id, operation);
        replaceAction(updated);
        setMessage("状态已保存。");
      }
    } catch (err) {
      setError(getErrorMessage(err, "状态更新失败"));
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSaveNote(group: ProductGroup): Promise<void> {
    const requestKey = `note-${group.key}`;
    const note = (noteDrafts[group.key] ?? "").trim();
    setError("");
    setMessage("");
    setBusyKey(requestKey);
    try {
      const updated = await updateActionProductGroupNote(group.key, note || null);
      setActions((current) =>
        current.map((action) =>
          getProductGroupKey(action) === group.key
            ? {
                ...action,
                product_note: updated.note,
                product_sort_order: updated.sort_order,
              }
            : action,
        ),
      );
      setNoteDrafts((current) => ({ ...current, [group.key]: updated.note ?? "" }));
      setMessage("产品备注已保存。");
    } catch (err) {
      setError(getErrorMessage(err, "产品备注保存失败"));
    } finally {
      setBusyKey(null);
    }
  }

  async function handleMoveProduct(groupIndex: number, direction: -1 | 1): Promise<void> {
    const targetIndex = groupIndex + direction;
    if (targetIndex < 0 || targetIndex >= groups.length) {
      return;
    }

    const nextGroups = swapAt(groups, groupIndex, targetIndex);
    const nextKeys = nextGroups.map((group) => group.key);
    const previousActions = actions;

    setSelectedProductKey(groups[groupIndex].key);
    setActions((current) =>
      current.map((action) => {
        const nextSortOrder = nextKeys.indexOf(getProductGroupKey(action));
        return nextSortOrder === -1 ? action : { ...action, product_sort_order: nextSortOrder };
      }),
    );
    setError("");
    setMessage("");
    setBusyKey(`product-order-${groups[groupIndex].key}`);

    try {
      await reorderActionProductGroups(nextKeys);
      setMessage("产品排序已保存。");
    } catch (err) {
      setActions(previousActions);
      setError(getErrorMessage(err, "产品排序保存失败"));
    } finally {
      setBusyKey(null);
    }
  }

  async function handleMoveAction(group: ProductGroup, actionIndex: number, direction: -1 | 1): Promise<void> {
    const targetIndex = actionIndex + direction;
    if (targetIndex < 0 || targetIndex >= group.actions.length) {
      return;
    }

    const nextActions = swapAt(group.actions, actionIndex, targetIndex);
    const nextIds = nextActions.map((action) => action.id);
    const previousActions = actions;

    setActions((current) =>
      current.map((action) => {
        const nextSortOrder = nextIds.indexOf(action.id);
        return nextSortOrder === -1 ? action : { ...action, sort_order: nextSortOrder };
      }),
    );
    setError("");
    setMessage("");
    setBusyKey(`action-order-${group.key}`);

    try {
      await reorderActionItems(group.key, nextIds);
      setMessage("行动排序已保存。");
    } catch (err) {
      setActions(previousActions);
      setError(getErrorMessage(err, "行动排序保存失败"));
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSaveSuggestions(action: ActionItem, nextSuggestions: string[]): Promise<void> {
    const cleaned = cleanSuggestions(nextSuggestions);
    const requestKey = `suggestions-${action.id}`;
    setError("");
    setMessage("");
    setBusyKey(requestKey);
    try {
      const updated = await updateActionSuggestions(action.id, cleaned);
      replaceAction(updated);
      setSuggestionDrafts((current) => ({ ...current, [action.id]: parseSuggestions(updated) }));
      setMessage("AI 建议已保存。");
    } catch (err) {
      setError(getErrorMessage(err, "AI 建议保存失败"));
    } finally {
      setBusyKey(null);
    }
  }

  async function handleConfirmRemove(): Promise<void> {
    if (!confirmTarget) {
      return;
    }

    setError("");
    setMessage("");
    setBusyKey("remove");
    try {
      if (confirmTarget.type === "product") {
        await removeActionProductGroup(confirmTarget.group.key);
        setActions((current) => current.filter((action) => getProductGroupKey(action) !== confirmTarget.group.key));
        setNoteDrafts((current) => {
          const next = { ...current };
          delete next[confirmTarget.group.key];
          return next;
        });
        setExpandedProductKeys((current) => removeFromSet(current, confirmTarget.group.key));
        setSelectedProductKey(null);
        setMessage("该产品下的行动和备注已从行动中心移除。");
      } else {
        await deleteActionItem(confirmTarget.action.id);
        setActions((current) => current.filter((action) => action.id !== confirmTarget.action.id));
        setExpandedActionIds((current) => removeFromSet(current, confirmTarget.action.id));
        setMessage("行动已从行动中心移除。");
      }
      setConfirmTarget(null);
    } catch (err) {
      setError(getErrorMessage(err, "移除失败"));
    } finally {
      setBusyKey(null);
    }
  }

  function replaceAction(updated: ActionItem): void {
    const normalized = normalizeActionItem(updated);
    setActions((current) => current.map((action) => (action.id === normalized.id ? normalized : action)));
  }

  function getSuggestions(action: ActionItem): string[] {
    return suggestionDrafts[action.id] ?? parseSuggestions(action);
  }

  function updateSuggestionDraft(action: ActionItem, index: number, value: string): void {
    const current = getSuggestions(action);
    const next = current.map((item, itemIndex) => (itemIndex === index ? value : item));
    setSuggestionDrafts((drafts) => ({ ...drafts, [action.id]: next }));
  }

  function addSuggestionDraft(action: ActionItem): void {
    setSuggestionDrafts((drafts) => ({ ...drafts, [action.id]: [...getSuggestions(action), ""] }));
    setExpandedActionIds((current) => addToSet(current, action.id));
  }

  if (actions.length === 0) {
    return (
      <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
        <h2 className="font-heading text-3xl font-extrabold tracking-normal text-ink">
          暂无行动事项
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
          先去分析结果页从 TOP 问题创建一个 action，或者从工作台里继续推进现有事项。
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur md:p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="inline-flex rounded-md bg-[#eef6ff] px-3 py-1.5 text-xs font-bold text-[#4a7dc7]">
            ACTION CENTER
          </div>
          <h2 className="mt-3 font-heading text-2xl font-extrabold tracking-normal text-ink">
            行动中心
          </h2>
        </div>

        <div className="flex flex-wrap gap-2">
          {FILTER_OPTIONS.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setActiveStatus(item.value)}
              className={cn(
                "min-h-9 rounded-md border px-3 py-2 text-sm font-semibold transition",
                activeStatus === item.value
                  ? "border-transparent bg-ink text-white shadow-card"
                  : "border-line bg-white text-soft hover:border-[#f36f8f]",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="mt-5 rounded-md border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
          {error}
        </div>
      ) : null}
      {message ? (
        <div className="mt-5 rounded-md border border-[#c9e8dc] bg-[#f6fffb] px-4 py-3 text-sm leading-7 text-[#3d8b74]">
          {message}
        </div>
      ) : null}

      <div className="mt-6 space-y-4">
        {groups.length === 0 ? (
          <div className="rounded-md border border-dashed border-line bg-white/70 px-5 py-8 text-sm leading-7 text-soft">
            当前筛选下暂无行动事项。
          </div>
        ) : null}

        {groups.map((group, groupIndex) => {
          const isExpanded = expandedProductKeys.has(group.key);
          const isSelected = selectedProductKey === group.key;
          const stats = getGroupStats(group.actions);
          const noteDraft = noteDrafts[group.key] ?? group.note ?? "";

          return (
            <article
              key={group.key}
              className={cn(
                "overflow-hidden rounded-md border bg-white transition",
                isSelected ? "border-[#f36f8f] shadow-card" : "border-line",
              )}
            >
              <div className="flex flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedProductKey(group.key);
                    setExpandedProductKeys((current) => toggleSetItem(current, group.key));
                  }}
                  className="flex min-w-0 flex-1 items-start gap-3 text-left"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-line bg-[#fafbff] text-ink">
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-base font-bold text-ink">{group.name}</span>
                    <span className="mt-1 block text-xs leading-6 text-soft">
                      {stats.total} 条行动 · {stats.reviewing} 个复盘中 · {stats.done} 个已完结
                    </span>
                  </span>
                </button>

                <div className="flex flex-wrap items-center gap-2">
                  <IconButton
                    label="上移产品"
                    disabled={groupIndex === 0 || busyKey !== null}
                    onClick={() => handleMoveProduct(groupIndex, -1)}
                  >
                    <ArrowUp className="h-4 w-4" />
                  </IconButton>
                  <IconButton
                    label="下移产品"
                    disabled={groupIndex === groups.length - 1 || busyKey !== null}
                    onClick={() => handleMoveProduct(groupIndex, 1)}
                  >
                    <ArrowDown className="h-4 w-4" />
                  </IconButton>
                  <button
                    type="button"
                    disabled={busyKey !== null}
                    onClick={() => {
                      setSelectedProductKey(group.key);
                      setConfirmTarget({ type: "product", group });
                    }}
                    className="min-h-9 rounded-md border border-[#f5c6cb] bg-white px-3 py-2 text-sm font-semibold text-[#b44655] transition hover:bg-[#fff3f5] disabled:opacity-60"
                  >
                    移除
                  </button>
                </div>
              </div>

              {isExpanded ? (
                <div className="border-t border-line bg-[#fbfcff] px-4 py-4">
                  <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-start">
                    <Textarea
                      value={noteDraft}
                      onChange={(event) =>
                        setNoteDrafts((current) => ({ ...current, [group.key]: event.target.value }))
                      }
                      placeholder="添加产品备注"
                      aria-label={`${group.name} 产品备注`}
                      className="min-h-20 resize-y rounded-md bg-white text-sm"
                    />
                    <Button
                      type="button"
                      disabled={busyKey !== null}
                      onClick={() => handleSaveNote(group)}
                      className="min-h-10 rounded-md bg-ink px-4 text-sm text-white"
                    >
                      <Save className="h-4 w-4" />
                      保存备注
                    </Button>
                  </div>

                  <div className="mt-4 divide-y divide-line rounded-md border border-line bg-white">
                    {group.actions.map((action, actionIndex) => {
                      const status = normalizeStatus(action.status);
                      const actionExpanded = expandedActionIds.has(action.id);
                      const suggestions = getSuggestions(action);

                      return (
                        <div key={action.id} className="px-4 py-4">
                          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                            <button
                              type="button"
                              onClick={() => setExpandedActionIds((current) => toggleSetItem(current, action.id))}
                              className="flex min-w-0 flex-1 items-start gap-3 text-left"
                            >
                              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-line bg-[#fafbff] text-ink">
                                {actionExpanded ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </span>
                              <span className="min-w-0">
                                <span className="block text-sm font-bold leading-6 text-ink">{action.title}</span>
                                <span className="mt-1 block text-xs leading-6 text-soft">
                                  {formatJoinedDate(action.created_at)} · {getActionSourceLine(action)}
                                </span>
                              </span>
                            </button>

                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={cn(
                                  "inline-flex min-h-8 items-center rounded-md border px-3 text-xs font-semibold",
                                  STATUS_BADGE_CLASS[status],
                                )}
                              >
                                {STATUS_LABELS[status]}
                              </span>
                              <select
                                value=""
                                disabled={busyKey !== null}
                                onChange={(event) => {
                                  const operation = event.target.value as StatusOperation;
                                  if (operation) {
                                    void handleStatusOperation(action, operation);
                                  }
                                }}
                                aria-label={`${action.title} 状态动作`}
                                className="h-9 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink outline-none transition focus:border-[#f36f8f] disabled:opacity-60"
                              >
                                <option value="" disabled>
                                  状态动作
                                </option>
                                {STATUS_OPERATIONS.map((item) => (
                                  <option key={item.value} value={item.value}>
                                    {item.label}
                                  </option>
                                ))}
                              </select>
                              <IconButton
                                label="上移行动"
                                disabled={actionIndex === 0 || busyKey !== null}
                                onClick={() => handleMoveAction(group, actionIndex, -1)}
                              >
                                <ArrowUp className="h-4 w-4" />
                              </IconButton>
                              <IconButton
                                label="下移行动"
                                disabled={actionIndex === group.actions.length - 1 || busyKey !== null}
                                onClick={() => handleMoveAction(group, actionIndex, 1)}
                              >
                                <ArrowDown className="h-4 w-4" />
                              </IconButton>
                              <IconButton
                                label="移除行动"
                                disabled={busyKey !== null}
                                className="border-[#f5c6cb] text-[#b44655] hover:bg-[#fff3f5]"
                                onClick={() => setConfirmTarget({ type: "action", action })}
                              >
                                <Trash2 className="h-4 w-4" />
                              </IconButton>
                            </div>
                          </div>

                          {actionExpanded ? (
                            <div className="mt-4 border-l-2 border-[#f36f8f] pl-4">
                              <dl className="grid overflow-hidden rounded-md border border-line bg-line md:grid-cols-2 xl:grid-cols-3">
                                {getActionDetails(action).map((detail) => (
                                  <div key={detail.label} className="min-h-20 bg-white px-4 py-3">
                                    <dt className="text-xs font-semibold text-soft">{detail.label}</dt>
                                    <dd className="mt-2 whitespace-pre-wrap text-sm leading-7 text-ink">{detail.value}</dd>
                                  </div>
                                ))}
                              </dl>

                              <div className="mt-5">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                  <h4 className="text-sm font-bold text-ink">AI 建议</h4>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    disabled={busyKey !== null}
                                    onClick={() => addSuggestionDraft(action)}
                                    className="rounded-md"
                                  >
                                    <Plus className="h-4 w-4" />
                                    新增建议
                                  </Button>
                                </div>

                                <div className="mt-3 space-y-3">
                                  {suggestions.length === 0 ? (
                                    <div className="rounded-md border border-dashed border-line bg-[#fbfcff] px-4 py-4 text-sm text-soft">
                                      暂无 AI 建议。
                                    </div>
                                  ) : null}

                                  {suggestions.map((suggestion, suggestionIndex) => (
                                    <div
                                      key={`${action.id}-${suggestionIndex}`}
                                      className="grid gap-2 rounded-md border border-line bg-[#fbfcff] p-3 md:grid-cols-[2.5rem_1fr_auto] md:items-start"
                                    >
                                      <div className="text-sm font-bold leading-9 text-ink">
                                        {suggestionIndex + 1}、
                                      </div>
                                      <Textarea
                                        value={suggestion}
                                        rows={1}
                                        onChange={(event) =>
                                          updateSuggestionDraft(action, suggestionIndex, event.target.value)
                                        }
                                        aria-label={`${action.title} AI 建议 ${suggestionIndex + 1}`}
                                        className="min-h-9 resize-y rounded-md bg-white text-sm"
                                      />
                                      <div className="flex gap-2">
                                        <IconButton
                                          label="保存建议"
                                          disabled={busyKey !== null || !suggestion.trim()}
                                          onClick={() => handleSaveSuggestions(action, suggestions)}
                                        >
                                          <Save className="h-4 w-4" />
                                        </IconButton>
                                        <IconButton
                                          label="删除建议"
                                          disabled={busyKey !== null}
                                          className="border-[#f5c6cb] text-[#b44655] hover:bg-[#fff3f5]"
                                          onClick={() =>
                                            handleSaveSuggestions(
                                              action,
                                              suggestions.filter((_, index) => index !== suggestionIndex),
                                            )
                                          }
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </IconButton>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      <Dialog open={confirmTarget !== null} onOpenChange={(open) => !open && setConfirmTarget(null)}>
        <DialogContent className="rounded-md">
          <DialogHeader>
            <DialogTitle>
              {confirmTarget?.type === "product" ? "从行动中心移除该产品行动？" : "从行动中心移除这条行动？"}
            </DialogTitle>
            <DialogDescription className="leading-7">
              {confirmTarget?.type === "product"
                ? "这将移除该产品下所有已加入行动中心的行动事项和备注，但不会删除产品、评论数据或分析结果。"
                : "这将只把该行动从行动中心移除，不会删除产品、评论数据或分析结果。"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={busyKey === "remove"}
              onClick={() => setConfirmTarget(null)}
            >
              取消
            </Button>
            <Button
              type="button"
              disabled={busyKey === "remove"}
              onClick={handleConfirmRemove}
              className="bg-[#b44655] text-white hover:bg-[#963746]"
            >
              确认移除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function IconButton({
  label,
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className={cn(
        "flex h-9 w-9 items-center justify-center rounded-md border border-line bg-white text-ink transition hover:border-[#f36f8f] hover:bg-[#fffafb] disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

function normalizeActionItem(item: ActionItem): ActionItem {
  return {
    ...item,
    status: normalizeStatus(item.status),
    ai_suggestions_json: Array.isArray(item.ai_suggestions_json) ? item.ai_suggestions_json : [],
    source_reviews_json: Array.isArray(item.source_reviews_json) ? item.source_reviews_json : [],
  };
}

function normalizeStatus(status: string | null | undefined): ActionDisplayStatus {
  if (status === "pending_review") {
    return "pending_review";
  }
  if (status === "done") {
    return "done";
  }
  return "in_progress";
}

function buildProductGroups(items: ActionItem[]): ProductGroup[] {
  const groupMap = new Map<string, ProductGroup>();

  for (const action of items) {
    const key = getProductGroupKey(action);
    const existing = groupMap.get(key);
    if (existing) {
      existing.actions.push(action);
      if (!existing.note && action.product_note) {
        existing.note = action.product_note;
      }
      if (existing.sortOrder == null && action.product_sort_order != null) {
        existing.sortOrder = action.product_sort_order;
      }
      continue;
    }

    groupMap.set(key, {
      key,
      name: getProductGroupName(action),
      note: action.product_note ?? "",
      sortOrder: action.product_sort_order ?? null,
      actions: [action],
    });
  }

  return Array.from(groupMap.values())
    .map((group) => ({
      ...group,
      actions: [...group.actions].sort(compareActions),
    }))
    .sort(compareGroups);
}

function compareGroups(a: ProductGroup, b: ProductGroup): number {
  const aOrder = a.sortOrder ?? Number.MAX_SAFE_INTEGER;
  const bOrder = b.sortOrder ?? Number.MAX_SAFE_INTEGER;
  if (aOrder !== bOrder) {
    return aOrder - bOrder;
  }
  return a.name.localeCompare(b.name, "zh-CN");
}

function compareActions(a: ActionItem, b: ActionItem): number {
  const aOrder = a.sort_order ?? Number.MAX_SAFE_INTEGER;
  const bOrder = b.sort_order ?? Number.MAX_SAFE_INTEGER;
  if (aOrder !== bOrder) {
    return aOrder - bOrder;
  }
  const aTime = Date.parse(a.created_at ?? "");
  const bTime = Date.parse(b.created_at ?? "");
  if (!Number.isNaN(aTime) && !Number.isNaN(bTime) && aTime !== bTime) {
    return bTime - aTime;
  }
  return b.id - a.id;
}

function getProductGroupKey(action: ActionItem): string {
  if (action.product_group_key) {
    return action.product_group_key;
  }
  if (action.product_id != null) {
    return `product:${action.product_id}`;
  }
  if (action.source_product_id) {
    return `source:${action.source_product_id}`;
  }
  if (action.session_id != null) {
    return `session:${action.session_id}`;
  }
  return "unbound";
}

function getProductGroupName(action: ActionItem): string {
  return (
    action.product_group_name ||
    action.product_name ||
    action.parent_product_id ||
    action.source_product_id ||
    (action.session_id ? `Session #${action.session_id}` : "未绑定产品")
  );
}

function getGroupStats(actions: ActionItem[]): { total: number; reviewing: number; done: number } {
  return {
    total: actions.length,
    reviewing: actions.filter((action) => normalizeStatus(action.status) === "pending_review").length,
    done: actions.filter((action) => normalizeStatus(action.status) === "done").length,
  };
}

function getActionDetails(action: ActionItem): Array<{ label: string; value: string }> {
  return [
    { label: "评论原文", value: formatSourceReviews(action) },
    { label: "Session", value: action.session_id ? `Session #${action.session_id}` : "—" },
    { label: "问题标签", value: action.tag_name || "—" },
    { label: "当前占比", value: formatPct(action.current_pct) },
    { label: "责任角色", value: action.owner_role || "—" },
    { label: "预计复盘", value: action.expected_review_at || "—" },
    { label: "来源版本", value: action.source_version || "—" },
    { label: "来源批次", value: action.source_batch_label || "—" },
    { label: "变体", value: action.variant_sku || action.child_asin || "—" },
  ];
}

function formatSourceReviews(action: ActionItem): string {
  const reviews = Array.isArray(action.source_reviews_json) ? action.source_reviews_json : [];
  const contents = reviews
    .map((review, index) => {
      const content = String(review.content || "").trim();
      return content ? `${index + 1}、${content}` : "";
    })
    .filter(Boolean);
  return contents.length > 0 ? contents.join("\n") : "—";
}

function getActionSourceLine(action: ActionItem): string {
  const parts = [
    action.source_product_id || action.parent_product_id || action.product_name || "未绑定产品",
    action.source_version || null,
    action.source_batch_label || null,
  ].filter(Boolean);
  return parts.join(" · ");
}

function getPrimarySuggestion(action: ActionItem): string | null {
  return parseSuggestions(action)[0] || action.suggested_action || null;
}

function parseSuggestions(action: ActionItem): string[] {
  const stored = Array.isArray(action.ai_suggestions_json)
    ? action.ai_suggestions_json.map((item) => cleanSuggestion(item)).filter(Boolean)
    : [];
  if (stored.length > 0) {
    return stored;
  }

  const raw = action.suggested_action?.trim();
  if (!raw) {
    return [];
  }
  const lines = raw
    .replace(/\r/g, "\n")
    .split(/\n+/)
    .map((line) => cleanSuggestion(line))
    .filter(Boolean);
  if (lines.length > 1) {
    return lines;
  }

  const numbered = raw
    .split(/(?=\d+[、.]\s*)/)
    .map((line) => cleanSuggestion(line))
    .filter(Boolean);
  return numbered.length > 1 ? numbered : [cleanSuggestion(raw)];
}

function cleanSuggestions(suggestions: string[]): string[] {
  return suggestions.map((item) => cleanSuggestion(item)).filter(Boolean);
}

function cleanSuggestion(value: string): string {
  return value.replace(/^\d+[、.]\s*/, "").trim();
}

function buildInitialNoteDrafts(items: ActionItem[]): Record<string, string> {
  return items.reduce<Record<string, string>>((drafts, item) => {
    const key = getProductGroupKey(item);
    if (!(key in drafts)) {
      drafts[key] = item.product_note ?? "";
    }
    return drafts;
  }, {});
}

function buildInitialSuggestionDrafts(items: ActionItem[]): Record<number, string[]> {
  return items.reduce<Record<number, string[]>>((drafts, item) => {
    drafts[item.id] = parseSuggestions(item);
    return drafts;
  }, {});
}

function formatJoinedDate(value: string | null): string {
  if (!value) {
    return "加入时间未记录";
  }
  const date = value.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(date) ? `加入于 ${date}` : "加入时间未记录";
}

function formatPct(value: number | null): string {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

function swapAt<T>(items: T[], index: number, targetIndex: number): T[] {
  const next = [...items];
  const current = next[index];
  next[index] = next[targetIndex];
  next[targetIndex] = current;
  return next;
}

function toggleSetItem<T>(items: Set<T>, value: T): Set<T> {
  const next = new Set(items);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

function addToSet<T>(items: Set<T>, value: T): Set<T> {
  const next = new Set(items);
  next.add(value);
  return next;
}

function removeFromSet<T>(items: Set<T>, value: T): Set<T> {
  const next = new Set(items);
  next.delete(value);
  return next;
}

function getErrorMessage(error: unknown, fallback: string): string {
  const candidate = error as { message?: string };
  return candidate.message || fallback;
}
