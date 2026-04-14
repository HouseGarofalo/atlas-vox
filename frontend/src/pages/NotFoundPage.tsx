import { useNavigate } from "react-router-dom";
import { ArrowLeft, Home, Mic, AudioLines, BookOpen } from "lucide-react";
import { Button } from "../components/ui/Button";
import WaveformVisualizer from "../components/audio/WaveformVisualizer";

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="relative mb-6">
        <h1 className="text-8xl font-display font-bold text-gradient">404</h1>
        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-32">
          <WaveformVisualizer height={16} barCount={10} animated={false} color="primary" />
        </div>
      </div>

      <h2 className="text-xl font-display font-semibold text-[var(--color-text)] mt-4">
        Page not found
      </h2>
      <p className="mt-2 max-w-md text-sm text-[var(--color-text-secondary)]">
        The page you are looking for does not exist or has been moved.
      </p>

      <div className="flex items-center gap-3 mt-8">
        <Button onClick={() => navigate("/")}>
          <Home className="h-4 w-4" /> Go to Dashboard
        </Button>
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" /> Go Back
        </Button>
      </div>

      <div className="mt-12 border-t border-[var(--color-border)] pt-6 w-full max-w-sm">
        <p className="text-xs text-[var(--color-text-tertiary)] mb-4">Try these instead:</p>
        <div className="flex justify-center gap-6">
          <button
            onClick={() => navigate("/synthesis")}
            className="flex flex-col items-center gap-2 text-[var(--color-text-secondary)] hover:text-primary-500 transition-colors"
          >
            <AudioLines className="h-5 w-5" />
            <span className="text-xs">Synthesis Lab</span>
          </button>
          <button
            onClick={() => navigate("/profiles")}
            className="flex flex-col items-center gap-2 text-[var(--color-text-secondary)] hover:text-primary-500 transition-colors"
          >
            <Mic className="h-5 w-5" />
            <span className="text-xs">Profiles</span>
          </button>
          <button
            onClick={() => navigate("/docs")}
            className="flex flex-col items-center gap-2 text-[var(--color-text-secondary)] hover:text-primary-500 transition-colors"
          >
            <BookOpen className="h-5 w-5" />
            <span className="text-xs">Docs</span>
          </button>
        </div>
      </div>
    </div>
  );
}
