"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Board,
  Difficulty,
  generatePuzzle,
  getConflicts,
  isBoardComplete,
  solvePuzzle,
} from "@/lib/sudoku";
import SudokuBoard from "./SudokuBoard";
import NumberPad from "./NumberPad";
import Timer from "./Timer";

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard", "expert"];

export default function SudokuGame() {
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [board, setBoard] = useState<Board>([]);
  const [initialBoard, setInitialBoard] = useState<Board>([]);
  const [solution, setSolution] = useState<Board>([]);
  const [selectedCell, setSelectedCell] = useState<[number, number] | null>(null);
  const [conflicts, setConflicts] = useState<Set<string>>(new Set());
  const [isComplete, setIsComplete] = useState(false);
  const [timerRunning, setTimerRunning] = useState(false);
  const [timerReset, setTimerReset] = useState(false);
  const [mistakes, setMistakes] = useState(0);
  const [notes, setNotes] = useState<Record<string, Set<number>>>({});
  const [noteMode, setNoteMode] = useState(false);
  const [history, setHistory] = useState<Board[]>([]);
  const [showComplete, setShowComplete] = useState(false);

  const newGame = useCallback((diff: Difficulty) => {
    const { puzzle, solution: sol } = generatePuzzle(diff);
    setBoard(puzzle.map((r) => [...r]));
    setInitialBoard(puzzle.map((r) => [...r]));
    setSolution(sol.map((r) => [...r]));
    setSelectedCell(null);
    setConflicts(new Set());
    setIsComplete(false);
    setTimerRunning(true);
    setTimerReset(true);
    setTimeout(() => setTimerReset(false), 50);
    setMistakes(0);
    setNotes({});
    setNoteMode(false);
    setHistory([]);
    setShowComplete(false);
  }, []);

  useEffect(() => {
    newGame(difficulty);
  }, []);

  const placeNumber = useCallback(
    (num: number) => {
      if (!selectedCell || isComplete) return;
      const [r, c] = selectedCell;
      if (initialBoard[r][c] !== null) return;

      if (noteMode) {
        const key = `${r}-${c}`;
        setNotes((prev) => {
          const cell = new Set(prev[key] ?? []);
          if (cell.has(num)) cell.delete(num);
          else cell.add(num);
          return { ...prev, [key]: cell };
        });
        return;
      }

      setHistory((h) => [...h, board.map((row) => [...row])]);
      const newBoard = board.map((row) => [...row]) as Board;
      newBoard[r][c] = newBoard[r][c] === num ? null : num;

      // clear notes for same row/col/box when placing number
      if (newBoard[r][c] !== null) {
        const n = num;
        setNotes((prev) => {
          const updated = { ...prev };
          for (let i = 0; i < 9; i++) {
            const rk = `${r}-${i}`;
            const ck = `${i}-${c}`;
            if (updated[rk]) { const s = new Set(updated[rk]); s.delete(n); updated[rk] = s; }
            if (updated[ck]) { const s = new Set(updated[ck]); s.delete(n); updated[ck] = s; }
          }
          const br = Math.floor(r / 3) * 3, bc = Math.floor(c / 3) * 3;
          for (let rr = br; rr < br + 3; rr++) {
            for (let cc = bc; cc < bc + 3; cc++) {
              const bk = `${rr}-${cc}`;
              if (updated[bk]) { const s = new Set(updated[bk]); s.delete(n); updated[bk] = s; }
            }
          }
          return updated;
        });
      }

      const newConflicts = getConflicts(newBoard);
      setConflicts(newConflicts);

      if (newBoard[r][c] !== null && newBoard[r][c] !== solution[r][c]) {
        setMistakes((m) => m + 1);
      }

      setBoard(newBoard);
      if (isBoardComplete(newBoard, solution)) {
        setIsComplete(true);
        setTimerRunning(false);
        setShowComplete(true);
      }
    },
    [selectedCell, isComplete, initialBoard, noteMode, board, solution]
  );

  const erase = useCallback(() => {
    if (!selectedCell || isComplete) return;
    const [r, c] = selectedCell;
    if (initialBoard[r][c] !== null) return;
    const key = `${r}-${c}`;
    if (notes[key]?.size) {
      setNotes((prev) => ({ ...prev, [key]: new Set() }));
      return;
    }
    setHistory((h) => [...h, board.map((row) => [...row])]);
    const newBoard = board.map((row) => [...row]) as Board;
    newBoard[r][c] = null;
    setBoard(newBoard);
    setConflicts(getConflicts(newBoard));
  }, [selectedCell, isComplete, initialBoard, board, notes]);

  const undo = useCallback(() => {
    if (history.length === 0) return;
    const prev = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setBoard(prev.map((r) => [...r]));
    setConflicts(getConflicts(prev));
  }, [history]);

  const hint = useCallback(() => {
    if (!selectedCell || isComplete) return;
    const [r, c] = selectedCell;
    if (initialBoard[r][c] !== null) return;
    setHistory((h) => [...h, board.map((row) => [...row])]);
    const newBoard = board.map((row) => [...row]) as Board;
    newBoard[r][c] = solution[r][c];
    setBoard(newBoard);
    setConflicts(getConflicts(newBoard));
    if (isBoardComplete(newBoard, solution)) {
      setIsComplete(true);
      setTimerRunning(false);
      setShowComplete(true);
    }
  }, [selectedCell, isComplete, initialBoard, board, solution]);

  const handleSolve = useCallback(() => {
    const solved = solvePuzzle(board);
    if (solved) {
      setBoard(solved.map((r) => [...r]));
      setConflicts(new Set());
      setIsComplete(true);
      setTimerRunning(false);
    }
  }, [board]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key >= "1" && e.key <= "9") placeNumber(parseInt(e.key));
      if (e.key === "Backspace" || e.key === "Delete" || e.key === "0") erase();
      if (e.key === "n" || e.key === "N") setNoteMode((m) => !m);
      if ((e.ctrlKey || e.metaKey) && e.key === "z") { e.preventDefault(); undo(); }
      if (!selectedCell) return;
      const [r, c] = selectedCell;
      const moves: Record<string, [number, number]> = {
        ArrowUp: [Math.max(0, r - 1), c],
        ArrowDown: [Math.min(8, r + 1), c],
        ArrowLeft: [r, Math.max(0, c - 1)],
        ArrowRight: [r, Math.min(8, c + 1)],
      };
      if (moves[e.key]) {
        e.preventDefault();
        setSelectedCell(moves[e.key]);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [placeNumber, erase, undo, selectedCell]);

  if (board.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="game-container">
      {/* Header */}
      <header className="game-header">
        <div className="logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#logoGrad)" />
            <rect x="4" y="4" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.9" />
            <rect x="12.5" y="4" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.6" />
            <rect x="21" y="4" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.9" />
            <rect x="4" y="12.5" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.6" />
            <rect x="12.5" y="12.5" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.9" />
            <rect x="21" y="12.5" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.6" />
            <rect x="4" y="21" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.9" />
            <rect x="12.5" y="21" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.6" />
            <rect x="21" y="21" width="7" height="7" rx="1.5" fill="white" fillOpacity="0.9" />
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1" />
                <stop offset="1" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
          </svg>
          <span>Sudoku</span>
        </div>
        <Timer running={timerRunning} reset={timerReset} />
      </header>

      {/* Difficulty */}
      <div className="difficulty-bar">
        {DIFFICULTIES.map((d) => (
          <button
            key={d}
            onClick={() => {
              setDifficulty(d);
              newGame(d);
            }}
            className={`diff-btn${difficulty === d ? " diff-btn-active" : ""}`}
          >
            {d.charAt(0).toUpperCase() + d.slice(1)}
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="stats-row">
        <div className="stat">
          <span className="stat-label">Mistakes</span>
          <span className="stat-value text-red-500">{mistakes}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Notes</span>
          <button
            onClick={() => setNoteMode((m) => !m)}
            className={`note-toggle${noteMode ? " note-toggle-on" : ""}`}
          >
            {noteMode ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      {/* Board */}
      <div className="board-wrapper">
        <SudokuBoard
          board={board}
          initialBoard={initialBoard}
          selectedCell={selectedCell}
          conflicts={conflicts}
          solution={solution}
          onCellClick={(r, c) =>
            setSelectedCell((prev) =>
              prev?.[0] === r && prev?.[1] === c ? null : [r, c]
            )
          }
        />
        {/* Note overlays */}
        <div className="notes-overlay" aria-hidden>
          {board.map((row, r) =>
            row.map((val, c) => {
              const key = `${r}-${c}`;
              const cellNotes = notes[key];
              if (!cellNotes?.size || val !== null) return null;
              return (
                <div key={key} className="note-cell" style={{ gridRow: r + 1, gridColumn: c + 1 }}>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
                    <span key={n} className="note-num">
                      {cellNotes.has(n) ? n : ""}
                    </span>
                  ))}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Number Pad */}
      <NumberPad
        onNumber={placeNumber}
        onErase={erase}
        board={board}
        selectedCell={selectedCell}
      />

      {/* Controls */}
      <div className="controls">
        <button onClick={undo} disabled={history.length === 0} className="ctrl-btn" title="Undo (Ctrl+Z)">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
            <path d="M3 7v6h6" />
            <path d="M21 17a9 9 0 00-9-9 9 9 0 00-6 2.3L3 13" />
          </svg>
          Undo
        </button>
        <button onClick={hint} disabled={!selectedCell || isComplete} className="ctrl-btn" title="Hint">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          Hint
        </button>
        <button onClick={handleSolve} disabled={isComplete} className="ctrl-btn" title="Auto-solve">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          Solve
        </button>
        <button onClick={() => newGame(difficulty)} className="ctrl-btn new-btn" title="New game">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
            <path d="M21.5 2v6h-6" />
            <path d="M2.5 12a10 10 0 0117.8-6.3L21.5 8" />
            <path d="M2.5 22v-6h6" />
            <path d="M21.5 12a10 10 0 01-17.8 6.3L2.5 16" />
          </svg>
          New
        </button>
      </div>

      {/* Win Modal */}
      {showComplete && (
        <div className="modal-backdrop" onClick={() => setShowComplete(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-icon">🎉</div>
            <h2 className="modal-title">Puzzle Complete!</h2>
            <p className="modal-sub">
              Difficulty: <strong>{difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}</strong>
            </p>
            <p className="modal-sub">Mistakes: <strong>{mistakes}</strong></p>
            <div className="modal-actions">
              <button onClick={() => newGame(difficulty)} className="modal-btn modal-btn-primary">
                Play Again
              </button>
              <button onClick={() => setShowComplete(false)} className="modal-btn modal-btn-ghost">
                Review
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
