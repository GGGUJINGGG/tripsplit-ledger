import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

// Only worth showing once there's meaningfully more page above the
// fold than below it — otherwise it just clutters a short page.
const SHOW_AFTER_PX = 400;

export default function BackToTopFab() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setVisible(window.scrollY > SHOW_AFTER_PX);
    }
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      className="fab back-to-top-fab"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Back to top"
      title="Back to top"
    >
      <ArrowUp size={20} />
    </button>
  );
}
