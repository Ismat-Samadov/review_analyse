"use client";

interface NumberPadProps {
  onNumber: (n: number) => void;
  onErase: () => void;
  board: (number | null)[][];
  selectedCell: [number, number] | null;
}

export default function NumberPad({ onNumber, onErase, board, selectedCell }: NumberPadProps) {
  const counts: Record<number, number> = {};
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const v = board[r][c];
      if (v) counts[v] = (counts[v] || 0) + 1;
    }
  }

  return (
    <div className="number-pad">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => {
        const completed = counts[n] === 9;
        const selectedVal = selectedCell ? board[selectedCell[0]][selectedCell[1]] : null;
        const isActive = selectedVal === n;
        return (
          <button
            key={n}
            onClick={() => onNumber(n)}
            disabled={completed}
            className={`num-btn${isActive ? " num-btn-active" : ""}${completed ? " num-btn-done" : ""}`}
            aria-label={`Place ${n}`}
          >
            <span className="num-digit">{n}</span>
            {!completed && (
              <span className="num-count">{9 - (counts[n] || 0)}</span>
            )}
          </button>
        );
      })}
      <button onClick={onErase} className="erase-btn" aria-label="Erase cell">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 mx-auto mb-0.5">
          <path d="M20 20H7L3 16l10-10 7 7-3.5 3.5" />
          <path d="M6.5 17.5l4-4" />
        </svg>
        <span className="text-[10px]">Erase</span>
      </button>
    </div>
  );
}
