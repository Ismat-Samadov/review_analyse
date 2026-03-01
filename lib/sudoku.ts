export type Board = (number | null)[][];
export type Difficulty = "easy" | "medium" | "hard" | "expert";

const DIFFICULTY_CLUES: Record<Difficulty, number> = {
  easy: 40,
  medium: 32,
  hard: 26,
  expert: 22,
};

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function isValid(board: number[][], row: number, col: number, num: number): boolean {
  for (let c = 0; c < 9; c++) {
    if (board[row][c] === num) return false;
  }
  for (let r = 0; r < 9; r++) {
    if (board[r][col] === num) return false;
  }
  const boxRow = Math.floor(row / 3) * 3;
  const boxCol = Math.floor(col / 3) * 3;
  for (let r = boxRow; r < boxRow + 3; r++) {
    for (let c = boxCol; c < boxCol + 3; c++) {
      if (board[r][c] === num) return false;
    }
  }
  return true;
}

function fillBoard(board: number[][]): boolean {
  for (let row = 0; row < 9; row++) {
    for (let col = 0; col < 9; col++) {
      if (board[row][col] === 0) {
        const nums = shuffle([1, 2, 3, 4, 5, 6, 7, 8, 9]);
        for (const num of nums) {
          if (isValid(board, row, col, num)) {
            board[row][col] = num;
            if (fillBoard(board)) return true;
            board[row][col] = 0;
          }
        }
        return false;
      }
    }
  }
  return true;
}

function countSolutions(board: (number | null)[][], limit = 2): number {
  for (let row = 0; row < 9; row++) {
    for (let col = 0; col < 9; col++) {
      if (board[row][col] === null) {
        let count = 0;
        for (let num = 1; num <= 9; num++) {
          const filled = board.map((r) => [...r]) as number[][];
          if (isValid(filled, row, col, num)) {
            filled[row][col] = num;
            count += countSolutions(filled.map((r) => r.map((v) => v === 0 ? null : v)) as (number | null)[][], limit - count);
            if (count >= limit) return count;
          }
        }
        return count;
      }
    }
  }
  return 1;
}

export function generatePuzzle(difficulty: Difficulty): { puzzle: Board; solution: Board } {
  const solution: number[][] = Array.from({ length: 9 }, () => Array(9).fill(0));
  fillBoard(solution);

  const puzzle: (number | null)[][] = solution.map((row) => [...row]);
  const cells = shuffle(
    Array.from({ length: 81 }, (_, i) => [Math.floor(i / 9), i % 9])
  );

  const clues = DIFFICULTY_CLUES[difficulty];
  let removed = 0;
  const target = 81 - clues;

  for (const [row, col] of cells) {
    if (removed >= target) break;
    const backup = puzzle[row][col];
    puzzle[row][col] = null;
    const testBoard = puzzle.map((r) => [...r]) as (number | null)[][];
    if (countSolutions(testBoard) !== 1) {
      puzzle[row][col] = backup;
    } else {
      removed++;
    }
  }

  return {
    puzzle: puzzle as Board,
    solution: solution.map((r) => [...r]) as Board,
  };
}

export function isValidPlacement(board: Board, row: number, col: number, num: number): boolean {
  for (let c = 0; c < 9; c++) {
    if (c !== col && board[row][c] === num) return false;
  }
  for (let r = 0; r < 9; r++) {
    if (r !== row && board[r][col] === num) return false;
  }
  const boxRow = Math.floor(row / 3) * 3;
  const boxCol = Math.floor(col / 3) * 3;
  for (let r = boxRow; r < boxRow + 3; r++) {
    for (let c = boxCol; c < boxCol + 3; c++) {
      if ((r !== row || c !== col) && board[r][c] === num) return false;
    }
  }
  return true;
}

export function isBoardComplete(board: Board, solution: Board): boolean {
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      if (board[r][c] !== solution[r][c]) return false;
    }
  }
  return true;
}

export function getConflicts(board: Board): Set<string> {
  const conflicts = new Set<string>();
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const val = board[r][c];
      if (val === null) continue;
      if (!isValidPlacement(board, r, c, val)) {
        conflicts.add(`${r}-${c}`);
      }
    }
  }
  return conflicts;
}

export function solvePuzzle(board: Board): Board | null {
  const b = board.map((r) => [...r]) as (number | null)[][];

  function solve(): boolean {
    for (let row = 0; row < 9; row++) {
      for (let col = 0; col < 9; col++) {
        if (b[row][col] === null) {
          for (let num = 1; num <= 9; num++) {
            const filled = b.map((r) => r.map((v) => (v === null ? 0 : v))) as number[][];
            if (isValid(filled, row, col, num)) {
              b[row][col] = num;
              if (solve()) return true;
              b[row][col] = null;
            }
          }
          return false;
        }
      }
    }
    return true;
  }

  return solve() ? (b as Board) : null;
}
