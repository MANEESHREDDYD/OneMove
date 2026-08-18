import type { ReactNode } from "react";

import { AuthGate } from "../components/auth/auth-gate";
import { AuthProvider } from "../components/auth/auth-provider";
import { NavigationHeader } from "../components/navigation";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata = {
  title: "ZonePilot Observatory",
  description: "Evidence-backed network and provider state for ZonePilot.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground min-h-screen">
        <AuthProvider>
          <AuthGate>
            <NavigationHeader />
            {children}
          </AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
