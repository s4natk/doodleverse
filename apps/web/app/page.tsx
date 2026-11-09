import { Hero } from "../components/Hero";
import { HowItWorks } from "../components/HowItWorks";
import { SiteFooter } from "../components/SiteFooter";
import { SiteHeader } from "../components/SiteHeader";
import { Studio } from "../components/Studio";
import { UnderTheHood } from "../components/UnderTheHood";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <section id="play" aria-label="Draw" className="mx-auto max-w-6xl px-3 sm:px-6">
          <Studio />
        </section>
        <HowItWorks />
        <UnderTheHood />
      </main>
      <SiteFooter />
    </>
  );
}
