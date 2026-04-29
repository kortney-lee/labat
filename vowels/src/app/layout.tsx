import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { baseMetadata } from "@/lib/seo";
import { GA_MEASUREMENT_ID } from "@/lib/analytics";

export const metadata: Metadata = baseMetadata();

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {GA_MEASUREMENT_ID ? (
          <>
            <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`} strategy="afterInteractive" />
            <Script id="ga4-init" strategy="afterInteractive">
              {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}window.gtag=gtag;gtag('js',new Date());gtag('config','${GA_MEASUREMENT_ID}');`}
            </Script>
          </>
        ) : null}
        <div className="mx-auto min-h-screen max-w-6xl px-4 py-5">
          <div className="mb-4 rounded-full border border-sky-200 bg-white/80 px-4 py-2 text-xs text-slate-600">
            Newsroom status: autonomous publishing active
          </div>
          <Header />
          <main className="mt-5">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
