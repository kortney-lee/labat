"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

export function LayoutChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const showHeader = pathname !== "/";

  return (
    <div className="min-h-screen">
      {showHeader ? (
        <div className="sticky top-0 z-20 border-b border-black/10 bg-white/90 backdrop-blur">
          <div className="mx-auto max-w-[1480px] px-4 py-3 md:px-8 md:py-4">
            <Header />
          </div>
        </div>
      ) : null}

      <main className={`mx-auto max-w-[1480px] px-4 pb-10 md:px-8 ${showHeader ? "mt-8" : "mt-4"}`}>{children}</main>
      <Footer />
    </div>
  );
}