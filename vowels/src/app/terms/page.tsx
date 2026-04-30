import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | Vowels.org",
  description: "Read the Terms of Service for Vowels.org, a nutrition education platform.",
};

export default function TermsPage() {
  return (
    <section className="news-card max-w-3xl mx-auto p-6 md:p-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Legal</p>
      <h1 className="mt-3 font-serif text-5xl leading-tight text-slate-950">Terms of Service</h1>
      <p className="mt-3 text-sm text-slate-500">Effective date: April 29, 2026 &nbsp;·&nbsp; Last updated: April 29, 2026</p>

      <div className="prose prose-slate mt-8 max-w-none prose-headings:font-serif prose-headings:text-slate-950 prose-p:text-slate-700 prose-a:text-brand">
        <h2>1. Acceptance of Terms</h2>
        <p>
          By accessing or using Vowels.org ("the Site"), you agree to be bound by these Terms of Service
          ("Terms"). If you do not agree to all of these Terms, do not use the Site.
        </p>

        <h2>2. Use of the Site</h2>
        <p>
          Vowels.org provides nutrition education content for informational purposes only. You may access
          and read content for personal, non-commercial use. You may not copy, reproduce, distribute,
          transmit, broadcast, display, sell, license, or otherwise exploit any content without prior
          written permission from Vowels.org.
        </p>

        <h2>3. Educational Content — Not Medical Advice</h2>
        <p>
          All content published on Vowels.org is for educational and informational purposes only. Nothing
          on this Site constitutes medical advice, diagnosis, or treatment. Always consult a qualified
          healthcare professional before making changes to your diet, exercise routine, or health regimen.
        </p>

        <h2>4. Advertising and Sponsored Content</h2>
        <p>
          Vowels.org displays third-party advertisements served by Google AdSense and other advertising
          partners. Sponsored content and partner placements are clearly labeled. Vowels.org is not
          responsible for the content, accuracy, or practices of third-party advertisers.
        </p>

        <h2>5. Subscriptions and Newsletter</h2>
        <p>
          Vowels.org offers a free newsletter subscription through Google Subscribe with Google (SwG).
          By subscribing you agree to receive periodic educational content. You may unsubscribe at any
          time through your Google account settings or by contacting us.
        </p>

        <h2>6. Intellectual Property</h2>
        <p>
          All original content, design, logos, and trademarks on this Site are the property of Vowels.org
          or its licensors. Unauthorized use may violate copyright, trademark, and other applicable laws.
        </p>

        <h2>7. User-Generated Content</h2>
        <p>
          If you submit any content to Vowels.org (such as comments or feedback), you grant Vowels.org a
          non-exclusive, royalty-free, perpetual license to use, reproduce, and display that content.
          You represent that you have the right to grant this license.
        </p>

        <h2>8. Disclaimer of Warranties</h2>
        <p>
          The Site is provided "as is" without warranties of any kind, either express or implied.
          Vowels.org does not warrant that the Site will be uninterrupted, error-free, or free of viruses
          or other harmful components.
        </p>

        <h2>9. Limitation of Liability</h2>
        <p>
          To the fullest extent permitted by law, Vowels.org shall not be liable for any indirect,
          incidental, special, consequential, or punitive damages arising from your use of the Site or
          reliance on any content published here.
        </p>

        <h2>10. Governing Law</h2>
        <p>
          These Terms are governed by and construed in accordance with the laws of the United States.
          Any disputes arising under these Terms shall be subject to the exclusive jurisdiction of the
          courts located in the United States.
        </p>

        <h2>11. Changes to These Terms</h2>
        <p>
          Vowels.org reserves the right to modify these Terms at any time. We will update the
          "Last updated" date above. Continued use of the Site after changes constitutes your
          acceptance of the revised Terms.
        </p>

        <h2>12. Contact</h2>
        <p>
          If you have questions about these Terms, please{" "}
          <a href="/contact">contact us</a>.
        </p>
      </div>
    </section>
  );
}
