/**
 * Mocks the API at the `getApiJson` boundary.
 *
 * There is no deployed ZonePilot backend, so every test drives the UI from
 * fixtures keyed by the exact path the component requests. An unmapped path
 * fails loudly rather than resolving to undefined, which keeps a renamed
 * endpoint from silently passing as an empty render.
 */
import { ApiError } from "../lib/api/client";

/** A fixture value, a thunk producing one, or an Error to reject with. */
export type RouteEntry = unknown | (() => unknown) | Error;
export type RouteMap = Record<string, RouteEntry>;

export function respondFromRoutes(routes: RouteMap) {
  return async function getApiJsonDouble<T>(path: string): Promise<T> {
    if (!(path in routes)) {
      throw new ApiError(
        `Test double has no fixture for "${path}".`,
        404,
        "FIXTURE_MISSING",
        null,
      );
    }
    const entry = routes[path];
    if (entry instanceof Error) throw entry;
    const value = typeof entry === "function" ? (entry as () => unknown)() : entry;
    // The route map is heterogeneous by nature; each value is produced by a
    // typed fixture builder, so this narrowing is checked at the call site.
    return value as T;
  };
}

/** Never settles — used to hold a component in its loading state. */
export function pendingForever(): Promise<never> {
  return new Promise<never>(() => {});
}
