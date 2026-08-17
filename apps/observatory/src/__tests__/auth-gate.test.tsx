import type { Session, User } from "@supabase/supabase-js";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthGate } from "../components/auth/auth-gate";
import { useAuth } from "../components/auth/auth-provider";

vi.mock("../components/auth/auth-provider", () => ({ useAuth: vi.fn() }));

type AuthValue = ReturnType<typeof useAuth>;

const signOut = vi.fn();
const signIn = vi.fn();

function testSession(): Session {
  const user: User = {
    id: "user-1",
    app_metadata: { workspace_id: "ws-1" },
    user_metadata: {},
    aud: "authenticated",
    created_at: "2026-01-01T00:00:00Z",
    email: "observer@example.com",
  };
  return {
    access_token: "token",
    refresh_token: "refresh",
    expires_in: 3600,
    token_type: "bearer",
    user,
  };
}

function authState(overrides: Partial<AuthValue> = {}): AuthValue {
  return {
    configured: true,
    loading: false,
    session: null,
    user: null,
    role: "AUTHENTICATED",
    workspaceId: null,
    signIn,
    signOut,
    ...overrides,
  };
}

function signedIn(overrides: Partial<AuthValue> = {}): AuthValue {
  const session = testSession();
  return authState({
    session,
    user: session.user,
    role: "OWNER",
    workspaceId: "ws-1",
    ...overrides,
  });
}

function Dashboard() {
  return <p>PROTECTED DASHBOARD</p>;
}

function renderGate(value: AuthValue) {
  vi.mocked(useAuth).mockReturnValue(value);
  return render(
    <AuthGate>
      <Dashboard />
    </AuthGate>,
  );
}

beforeEach(() => {
  vi.mocked(useAuth).mockReset();
});

describe("unauthenticated", () => {
  it("shows the login form and never the dashboard", () => {
    renderGate(authState());

    expect(screen.getByRole("heading", { name: "Observatory sign in" })).toBeInTheDocument();
    expect(screen.queryByText("PROTECTED DASHBOARD")).not.toBeInTheDocument();
  });

  it("offers labelled email and password fields", () => {
    renderGate(authState());

    expect(screen.getByLabelText("Email")).toBeRequired();
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("withholds the dashboard when a session exists but the user does not", () => {
    renderGate(authState({ session: testSession(), user: null }));

    expect(screen.getByRole("heading", { name: "Observatory sign in" })).toBeInTheDocument();
    expect(screen.queryByText("PROTECTED DASHBOARD")).not.toBeInTheDocument();
  });

  it("submits the typed credentials", async () => {
    const user = userEvent.setup();
    renderGate(authState());

    await user.type(screen.getByLabelText("Email"), "observer@example.com");
    await user.type(screen.getByLabelText("Password"), "hunter2");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(signIn).toHaveBeenCalledWith("observer@example.com", "hunter2");
  });

  it("announces an authentication failure in an alert", async () => {
    const user = userEvent.setup();
    signIn.mockRejectedValueOnce(new Error("Invalid login credentials"));
    renderGate(authState());

    await user.type(screen.getByLabelText("Email"), "observer@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid login credentials");
  });
});

describe("unconfigured deployment", () => {
  it("explains the missing configuration rather than showing a login form", () => {
    renderGate(authState({ configured: false }));

    expect(screen.getByRole("alert")).toHaveTextContent("Authentication configuration required");
    expect(screen.queryByRole("heading", { name: "Observatory sign in" })).not.toBeInTheDocument();
    expect(screen.queryByText("PROTECTED DASHBOARD")).not.toBeInTheDocument();
  });

  it("does not fabricate a development session", () => {
    const { container } = renderGate(authState({ configured: false }));

    expect(container.textContent).toContain("will not create or use a development JWT");
  });
});

describe("session verification in flight", () => {
  it("shows a polite status and withholds the dashboard", () => {
    renderGate(authState({ loading: true }));

    expect(screen.getByText("Verifying Supabase session...")).toHaveAttribute(
      "aria-live",
      "polite",
    );
    expect(screen.queryByText("PROTECTED DASHBOARD")).not.toBeInTheDocument();
  });
});

describe("authenticated", () => {
  it("renders the dashboard with the identity bar", () => {
    renderGate(signedIn());

    expect(screen.getByText("PROTECTED DASHBOARD")).toBeInTheDocument();
    expect(screen.getByText("OWNER")).toBeInTheDocument();
    expect(screen.getByText("Workspace ws-1")).toBeInTheDocument();
  });

  it("provides a skip link to the main content", () => {
    renderGate(signedIn());

    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute(
      "href",
      "#main-content",
    );
  });

  it("names the sign out control for screen readers", async () => {
    const user = userEvent.setup();
    renderGate(signedIn());

    const button = screen.getByRole("button", { name: "Sign out of ZonePilot Observatory" });
    await user.click(button);

    expect(signOut).toHaveBeenCalled();
  });

  it("falls back to the email when no workspace is assigned", () => {
    renderGate(signedIn({ workspaceId: null }));

    expect(screen.getByText("observer@example.com")).toBeInTheDocument();
  });

  it("reports a failed sign out without dropping the dashboard", async () => {
    const user = userEvent.setup();
    signOut.mockRejectedValueOnce(new Error("Network unreachable"));
    renderGate(signedIn());

    await user.click(screen.getByRole("button", { name: "Sign out of ZonePilot Observatory" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Network unreachable");
    expect(screen.getByText("PROTECTED DASHBOARD")).toBeInTheDocument();
  });
});
