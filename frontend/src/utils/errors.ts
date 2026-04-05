/**
 * Type-safe error message extraction.
 * Replaces `catch (e: any) { e.message }` with `catch (e: unknown) { getErrorMessage(e) }`.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "An unexpected error occurred";
}
