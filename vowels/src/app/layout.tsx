import type { Metadata } from "next";
import { Lora, Manrope } from "next/font/google";
import Script from "next/script";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { baseMetadata } from "@/lib/seo";
import { GA_MEASUREMENT_ID } from "@/lib/analytics";

const ADSENSE_CLIENT = process.env.NEXT_PUBLIC_ADSENSE_CLIENT || "";

const sans = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
});

const display = Lora({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = baseMetadata();

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable}`}>
      <body>
        {GA_MEASUREMENT_ID ? (
          <>
            <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`} strategy="afterInteractive" />
            <Script id="ga4-init" strategy="afterInteractive">
              {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}window.gtag=gtag;gtag('js',new Date());gtag('config','${GA_MEASUREMENT_ID}');`}
            </Script>
          </>
        ) : null}

        {ADSENSE_CLIENT ? (
          <Script
            id="adsense-lib"
            async
            strategy="afterInteractive"
            src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`}
            crossOrigin="anonymous"
          />
        ) : null}

        {/* Subscribe with Google — newsletter/reader revenue */}
        <Script src="https://news.google.com/swg/js/v1/swg-basic.js" strategy="afterInteractive" />
        <Script id="swg-basic-init" strategy="afterInteractive">
          {`(self.SWG_BASIC = self.SWG_BASIC || []).push(basicSubscriptions => {
  basicSubscriptions.init({
    type: "NewsArticle",
    isPartOfType: ["Product"],
    isPartOfProductId: "CAow9bDGDA:openaccess",
    clientOptions: { theme: "light", lang: "en" },
  });
});`}
        </Script>
        <div className="min-h-screen">
          <div className="sticky top-0 z-20 border-b border-black/10 bg-white/90 backdrop-blur">
            <div className="mx-auto max-w-[1480px] px-4 py-3 md:px-8 md:py-4">
              <Header />
            </div>
          </div>
          <main className="mx-auto mt-8 max-w-[1480px] px-4 pb-10 md:px-8">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
