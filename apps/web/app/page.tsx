import { Hero } from "../components/Hero";
import { HowItWorks } from "../components/HowItWorks";
import { SiteFooter } from "../components/SiteFooter";
import { SiteHeader } from "../components/SiteHeader";
import { UnderTheHood } from "../components/UnderTheHood";

export default function CoverPage() {
  return (
    <div id="sheet" className="sheet graph-paper">
      <SiteHeader />
      <main>
        <Hero />
        <HowItWorks />
        <UnderTheHood />
      </main>
      <SiteFooter />
    </div>
  );
}
