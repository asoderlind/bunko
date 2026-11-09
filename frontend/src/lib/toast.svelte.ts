export type ToastKind = "info" | "error";

export type ToastItem = {
  id: number;
  message: string;
  kind: ToastKind;
};

let nextId = 0;

/** Global, small toast queue. Rendered once by <Toasts /> in the shell. */
export const toasts = $state<ToastItem[]>([]);

export function dismissToast(id: number) {
  const index = toasts.findIndex((t) => t.id === id);
  if (index !== -1) toasts.splice(index, 1);
}

export function showToast(message: string, kind: ToastKind = "info", timeout = 5000) {
  const id = ++nextId;
  toasts.push({ id, message, kind });
  if (timeout > 0) setTimeout(() => dismissToast(id), timeout);
  return id;
}
