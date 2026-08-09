import "./globals.css";
export default function RootLayout({ children }: { children: any }) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground">{children}</body>
    </html>
  );
}
