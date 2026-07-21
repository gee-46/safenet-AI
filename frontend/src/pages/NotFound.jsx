import { Link } from "react-router-dom";
import { Button } from "../components/ui/Primitives";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-32 text-center">
      <span className="font-mono text-6xl font-semibold text-void-line">404</span>
      <p className="font-display text-lg text-ink">Signal lost.</p>
      <p className="max-w-sm text-sm text-ink-faint">This sector of the console doesn't exist.</p>
      <div className="flex gap-3">
        <Link to="/console"><Button variant="ghost">Open Console</Button></Link>
        <Link to="/"><Button variant="subtle">Back to homepage</Button></Link>
      </div>
    </div>
  );
}
