export const metadata = {
  title: "BlendGuard",
  description:
    "Build a diversified ETF portfolio from your goals, beliefs, and risk limits.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
