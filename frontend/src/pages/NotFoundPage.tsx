import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-6xl font-bold text-[var(--color-text-secondary)]">404</h1>
      <p className="mt-4 text-lg text-[var(--color-text-secondary)]">
        Page not found
      </p>
      <Button className="mt-6" onClick={() => navigate("/")}>
        Back to Dashboard
      </Button>
    </div>
  );
}
