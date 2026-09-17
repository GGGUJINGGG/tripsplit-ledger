import { RefreshCw } from "lucide-react";

interface RefreshFabProps {
  isRefreshing: boolean;
  onRefresh: () => void;
}

export default function RefreshFab({ isRefreshing, onRefresh }: RefreshFabProps) {
  return (
    <button
      className="fab refresh-fab"
      type="button"
      onClick={onRefresh}
      disabled={isRefreshing}
      aria-label="Refresh trip data"
      title="Refresh trip data"
    >
      <RefreshCw size={20} className={isRefreshing ? "spin-icon" : undefined} />
    </button>
  );
}
