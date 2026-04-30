import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | Vowels.org",
  description: "Learn how Vowels.org collects, uses, and protects your personal information.",
};

export default function PrivacyPage() {
  return (
    <section className="news-card max-w-3xl mx-auto p-6 md:p-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Legal</p>
      <h1 className="mt-3 font-serif text-5xl leading-tight text-slate-950">Privacy Policy</h1>
      <p className="mt-3 text-sm text-slate-500">Effective date: April 29, 2026 &nbsp;·&nbsp; Last updated: April 29, 2026</p>

      <div className="prose prose-slate mt-8 max-w-none prose-headings:font-serif prose-headings:text-slate-950 prose-p:text-slate-700 prose-a:text-brand">
        <h2>1. Overview</h2>
        <p>
          Vowels.org ("we", "us", "our") is committed to protecting your privacy. This Privacy Policy
          explains what information we collect, how we use it, and your rights regarding that information
          when you visit <strong>vowels.org</strong>.
        </p>

        <h2>2. Information We Collect</h2>
        <h3>Automatically Collected Data</h3>
        <p>
          When you visit the Site, we automatically collect certain information through analytics tools,
          including: pages viewed, time on site, referring URLs, browser type, device type, and approximate
          geographic location (country/region level). This data is aggregated and not linked to individual
          identities.
        </p>
        <h3>Newsletter / Subscription Data</h3>
        <p>
          If you subscribe via Subscribe with Google, your subscription is managed by Google. Vowels.org
          receives only subscription status — we do not receive your Google account credentials or payment
          information. Review{" "}
          <a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer">Google's Privacy Policy</a>{" "}
          for details on how Google handles your data.
        </p>
        <h3>Contact Form Data</h3>
        <p>
          If you contact us, we collect the name and email address you voluntarily provide in order to
          respond to your inquiry. This information is not shared with third parties.
        </p>

        <h2>3. Cookies and Tracking Technologies</h2>
        <p>
          Vowels.org uses the following technologies that may set cookies or use tracking pixels:
        </p>
        <ul>
          <li><strong>Google Analytics (GA4)</strong> — measures site traffic and user behavior. You can opt out using the{" "}
            <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noreferrer">Google Analytics Opt-out Browser Add-on</a>.
          </li>
          <li><strong>Google AdSense</strong> — serves interest-based advertisements. Managed under Google's advertising policies.</li>
          <li><strong>Subscribe with Google (SwG)</strong> — manages newsletter subscriptions via your Google account.</li>
        </ul>
        <p>
          You can control cookies through your browser settings. Disabling cookies may affect site functionality.
        </p>

        <h2>4. How We Use Your Information</h2>
        <ul>
          <li>To understand how content is used and improve the Site</li>
          <li>To serve relevant advertising through Google AdSense</li>
          <li>To deliver newsletters to subscribers</li>
          <li>To respond to inquiries submitted via the contact form</li>
          <li>To comply with legal obligations</li>
        </ul>

        <h2>5. Advertising</h2>
        <p>
          We use Google AdSense to display ads on Vowels.org. Google may use cookies to serve ads based
          on your prior visits to this Site or other sites. You can opt out of personalized advertising
          by visiting{" "}
          <a href="https://www.google.com/settings/ads" target="_blank" rel="noreferrer">Google Ads Settings</a>{" "}
          or{" "}
          <a href="https://optout.aboutads.info/" target="_blank" rel="noreferrer">optout.aboutads.info</a>.
        </p>

        <h2>6. Data Sharing and Sale</h2>
        <p>
          We do not sell your personal data. We do not share personal data with third parties except:
        </p>
        <ul>
          <li>With service providers who operate the Site on our behalf (e.g., Google Analytics, AdSense)</li>
          <li>When required by law, court order, or governmental authority</li>
          <li>To protect the rights and safety of Vowels.org and its users</li>
        </ul>

        <h2>7. Data Retention</h2>
        <p>
          Analytics data is retained per Google Analytics default retention settings (14 months). Contact
          form submissions are retained only as long as necessary to respond to your inquiry.
        </p>

        <h2>8. Your Rights</h2>
        <p>
          Depending on your location, you may have rights under applicable privacy laws (including GDPR,
          CCPA, and similar regulations) to:
        </p>
        <ul>
          <li>Access the personal data we hold about you</li>
          <li>Request correction or deletion of your data</li>
          <li>Opt out of certain data processing activities</li>
          <li>Lodge a complaint with a supervisory authority</li>
        </ul>
        <p>
          To exercise these rights, <a href="/contact">contact us</a>.
        </p>

        <h2>9. Children's Privacy</h2>
        <p>
          Vowels.org is not directed to children under the age of 13. We do not knowingly collect
          personal information from children. If you believe a child has provided us with personal data,
          please contact us and we will delete it.
        </p>

        <h2>10. External Links</h2>
        <p>
          The Site may contain links to third-party websites. We are not responsible for the privacy
          practices of those sites and encourage you to review their privacy policies.
        </p>

        <h2>11. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy periodically. We will update the "Last updated" date above.
          Continued use of the Site after changes constitutes acceptance of the revised policy.
        </p>

        <h2>12. Contact</h2>
        <p>
          If you have questions about this Privacy Policy, please{" "}
          <a href="/contact">contact us</a>.
        </p>
      </div>
    </section>
  );
}
