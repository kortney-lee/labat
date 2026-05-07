import type { Metadata } from "next";
import { Lora, Manrope } from "next/font/google";
import Script from "next/script";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { LayoutChrome } from "@/components/LayoutChrome";
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
        {/* Google Consent Mode v2 — must fire before gtag/AdSense load */}
        <Script id="consent-mode-init" strategy="beforeInteractive">
          {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}
gtag('consent','default',{
  ad_storage:'denied',
  ad_user_data:'denied',
  ad_personalization:'denied',
  analytics_storage:'denied',
  wait_for_update:500
});
gtag('set','ads_data_redaction',true);
gtag('set','url_passthrough',true);`}
        </Script>

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
          />
        ) : null}

        {/* Subscribe with Google — only on production domain to avoid CORS 403 on staging */}
        <Script id="swg-basic-init" strategy="afterInteractive">
          {`if(location.hostname==='vowels.org'){var s=document.createElement('script');s.src='https://news.google.com/swg/js/v1/swg-basic.js';s.onload=function(){(self.SWG_BASIC=self.SWG_BASIC||[]).push(function(b){b.init({type:'NewsArticle',isPartOfType:['Product'],isPartOfProductId:'CAow9bDGDA:openaccess',clientOptions:{theme:'light',lang:'en'}});});};document.head.appendChild(s);}`}
        </Script>
        <LayoutChrome>{children}</LayoutChrome>
      </body>
    </html>
  );
}
