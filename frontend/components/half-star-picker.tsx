'use client';

import { KeyboardEvent, MouseEvent } from 'react';
import { Star } from 'lucide-react';

interface HalfStarPickerProps {
  value: number | null;
  onChange: (value: number) => void;
  label: string;
  readOnly?: boolean;
}

const MAX_SCORE = 5;

function clampScore(score: number): number {
  return Math.min(MAX_SCORE, Math.max(1, Math.round(score * 2) / 2));
}

export function HalfStarPicker({ value, onChange, label, readOnly = false }: HalfStarPickerProps) {
  const current = value == null ? 0 : clampScore(value);

  const handleStarClick = (event: MouseEvent<HTMLButtonElement>, star: number) => {
    if (readOnly) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const isHalf = rect.width > 0 && event.clientX - rect.left < rect.width / 2;
    onChange(isHalf ? star - 0.5 : star);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (readOnly) return;
    const direction = event.key === 'ArrowRight' ? 0.5 : event.key === 'ArrowLeft' ? -0.5 : 0;
    if (direction === 0) return;
    event.preventDefault();
    onChange(clampScore((current || 1) + direction));
  };

  return (
    <div
      role="radiogroup"
      aria-label={label}
      aria-valuetext={value == null ? 'Not rated' : `${current} out of 5 stars`}
      tabIndex={readOnly ? -1 : 0}
      onKeyDown={handleKeyDown}
      className="inline-flex items-center gap-0.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const fill = current >= star ? 100 : current >= star - 0.5 ? 50 : 0;
        return (
          <button
            key={star}
            type="button"
            role="radio"
            aria-label={`Set ${star - 0.5} stars`}
            aria-pressed={current === star - 0.5}
            aria-checked={current >= star - 0.5 && current < star + 0.5}
            disabled={readOnly}
            onClick={(event) => handleStarClick(event, star)}
            className="relative h-7 w-7 p-0.5 text-muted-foreground transition-colors hover:text-amber-500 disabled:cursor-default"
          >
            <Star className="h-full w-full" strokeWidth={1.75} />
            {fill > 0 && (
              <span className="absolute inset-0.5 overflow-hidden" style={{ width: `${fill}%` }}>
                <Star className="h-full w-7 fill-amber-400 text-amber-400" strokeWidth={1.75} />
              </span>
            )}
          </button>
        );
      })}
      <span className="ml-1 min-w-8 text-sm tabular-nums text-muted-foreground" aria-hidden="true">
        {value == null ? '—' : current.toFixed(1)}
      </span>
    </div>
  );
}

