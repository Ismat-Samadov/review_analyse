"use client";

import { Board } from "@/lib/sudoku";

interface SudokuBoardProps {
  board: Board;
  initialBoard: Board;
  selectedCell: [number, number] | null;
  conflicts: Set<string>;
  solution: Board;
  onCellClick: (row: number, col: number) => void;
}

export default function SudokuBoard({
  board,
  initialBoard,
  selectedCell,
  conflicts,
  solution,
  onCellClick,
}: SudokuBoardProps) {
  return (
    <div className="sudoku-board">
      {board.map((row, r) =>
        row.map((val, c) => {
          const key = `${r}-${c}`;
          const isSelected = selectedCell?.[0] === r && selectedCell?.[1] === c;
          const isInitial = initialBoard[r][c] !== null;
          const isConflict = conflicts.has(key);
          const isSameNum =
            selectedCell &&
            board[selectedCell[0]][selectedCell[1]] !== null &&
            val === board[selectedCell[0]][selectedCell[1]];
          const isRelated =
            selectedCell &&
            (selectedCell[0] === r ||
              selectedCell[1] === c ||
              (Math.floor(selectedCell[0] / 3) === Math.floor(r / 3) &&
                Math.floor(selectedCell[1] / 3) === Math.floor(c / 3)));
          const isCorrect = val !== null && val === solution[r][c];

          const borderRight = (c + 1) % 3 === 0 && c !== 8 ? "border-r-[3px] border-r-[var(--box-border)]" : "border-r border-r-[var(--cell-border)]";
          const borderBottom = (r + 1) % 3 === 0 && r !== 8 ? "border-b-[3px] border-b-[var(--box-border)]" : "border-b border-b-[var(--cell-border)]";

          let bg = "var(--cell-bg)";
          if (isSelected) bg = "var(--selected-bg)";
          else if (isConflict) bg = "var(--conflict-bg)";
          else if (isSameNum && !isSelected) bg = "var(--same-num-bg)";
          else if (isRelated) bg = "var(--related-bg)";

          let textColor = "var(--initial-color)";
          if (!isInitial) {
            if (isConflict) textColor = "var(--conflict-color)";
            else if (isCorrect) textColor = "var(--correct-color)";
            else textColor = "var(--user-color)";
          }

          return (
            <button
              key={key}
              onClick={() => onCellClick(r, c)}
              className={`cell ${borderRight} ${borderBottom}`}
              style={{ backgroundColor: bg, color: textColor }}
              aria-label={`Row ${r + 1}, Column ${c + 1}${val ? `, value ${val}` : ", empty"}`}
            >
              {val ?? ""}
            </button>
          );
        })
      )}
    </div>
  );
}
