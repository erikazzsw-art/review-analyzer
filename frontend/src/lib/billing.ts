import { createBillingCheckout } from "@/lib/api/browser";
import type { BillingPeriod, PlanKey } from "@/lib/pricing";

/**
 * 拉起 Paddle checkout overlay。
 *
 * 流程：调 /api/billing/checkout 拿 checkout_html → 注入到宿主容器 → 依序执行内嵌 <script>
 * （Paddle 的 checkout_html 是 <script src="...paddle.js"> + <script>Paddle.Checkout.open(...)</script>，
 *   直接 innerHTML 塞进去浏览器不会执行 script，必须手动 replaceWith 一份新的 script 节点。）
 *
 * 调用方约定：
 * - 宿主容器建议 hidden + aria-hidden，Paddle overlay 自己会 fixed 定位。
 * - host 为 null 时会创建一个临时容器挂到 document.body。
 * - 401 会抛 { status: 401, message } —— 调用方通常应跳 /register?plan=<key>&period=<period> 或 /login。
 * - 若 !configured 表示后端未启用 Paddle；若 configured 但 !hasHtml 表示用户已有有效订阅。
 *
 * @returns OpenCheckoutResult
 */
export type OpenCheckoutResult = {
  ok: boolean;
  configured: boolean;
  hasHtml: boolean;
};

export async function openBillingCheckout(
  host?: HTMLElement | null,
  planKey?: PlanKey,
  period?: BillingPeriod,
): Promise<OpenCheckoutResult> {
  const result = await createBillingCheckout({ planKey, period });
  if (!result.configured) {
    return { ok: false, configured: false, hasHtml: false };
  }
  if (!result.checkout_html) {
    return { ok: false, configured: true, hasHtml: false };
  }

  let container = host ?? null;
  let createdEphemeral = false;
  if (!container) {
    container = document.createElement("div");
    container.setAttribute("aria-hidden", "true");
    container.style.display = "none";
    document.body.appendChild(container);
    createdEphemeral = true;
  }

  container.innerHTML = result.checkout_html;
  const scripts = Array.from(container.querySelectorAll("script"));
  for (const script of scripts) {
    await new Promise<void>((resolve, reject) => {
      const next = document.createElement("script");
      Array.from(script.attributes).forEach((attr) =>
        next.setAttribute(attr.name, attr.value),
      );
      if (next.src) {
        next.onload = () => resolve();
        next.onerror = () => reject(new Error("加载脚本失败"));
      } else {
        next.text = script.textContent || "";
        resolve();
      }
      script.replaceWith(next);
    });
  }

  // 临时容器不主动清理 —— Paddle 内嵌 script 可能在后续操作时回读 DOM
  void createdEphemeral;

  return { ok: true, configured: true, hasHtml: true };
}

/** Paddle checkout 后端返回 401 的辨识 —— 未登录 */
export function isUnauthenticatedCheckoutError(err: unknown): boolean {
  return (err as { status?: number } | null)?.status === 401;
}
