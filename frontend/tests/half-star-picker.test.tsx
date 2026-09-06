import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { HalfStarPicker } from '@/components/half-star-picker';

describe('HalfStarPicker', () => {
  it('renders the current half-star value accessibly', () => {
    render(<HalfStarPicker label="Fit" value={3.5} onChange={vi.fn()} />);

    expect(screen.getByRole('radiogroup', { name: 'Fit' })).toHaveAttribute(
      'aria-valuetext',
      '3.5 out of 5 stars',
    );
    expect(screen.getByRole('radio', { name: 'Set 3.5 stars' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('selects a rating and supports half-star keyboard steps', () => {
    const onChange = vi.fn();
    render(<HalfStarPicker label="Style" value={2} onChange={onChange} />);
    const group = screen.getByRole('radiogroup', { name: 'Style' });

    fireEvent.click(screen.getByRole('radio', { name: 'Set 3.5 stars' }));
    fireEvent.keyDown(group, { key: 'ArrowRight' });
    fireEvent.keyDown(group, { key: 'ArrowLeft' });

    expect(onChange).toHaveBeenNthCalledWith(1, 4);
    expect(onChange).toHaveBeenNthCalledWith(2, 2.5);
    expect(onChange).toHaveBeenNthCalledWith(3, 1.5);
  });
});
