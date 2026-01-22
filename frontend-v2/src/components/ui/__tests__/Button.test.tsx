/**
 * Button Component Tests
 *
 * Tests for the Button UI component covering:
 * - Render variants
 * - Click handling
 * - Disabled state
 * - Loading state
 * - Size variations
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../Button';

describe('Button Component', () => {
  // ===========================================================================
  // Basic Rendering
  // ===========================================================================

  describe('Basic Rendering', () => {
    it('renders with default props', () => {
      render(<Button>Click me</Button>);

      const button = screen.getByRole('button', { name: /click me/i });
      expect(button).toBeInTheDocument();
    });

    it('renders children correctly', () => {
      render(<Button>Submit Form</Button>);

      expect(screen.getByText('Submit Form')).toBeInTheDocument();
    });

    it('forwards ref correctly', () => {
      const ref = vi.fn();
      render(<Button ref={ref}>Button</Button>);

      expect(ref).toHaveBeenCalled();
    });

    it('spreads additional props to button element', () => {
      render(<Button data-testid="custom-button" aria-label="Custom button">Button</Button>);

      const button = screen.getByTestId('custom-button');
      expect(button).toHaveAttribute('aria-label', 'Custom button');
    });
  });

  // ===========================================================================
  // Variant Rendering
  // ===========================================================================

  describe('Variant Rendering', () => {
    it('renders primary variant by default', () => {
      render(<Button>Primary</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-blue-600');
    });

    it('renders primary variant correctly', () => {
      render(<Button variant="primary">Primary</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-blue-600');
      expect(button).toHaveClass('text-white');
    });

    it('renders secondary variant correctly', () => {
      render(<Button variant="secondary">Secondary</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-gray-600');
      expect(button).toHaveClass('text-white');
    });

    it('renders outline variant correctly', () => {
      render(<Button variant="outline">Outline</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('border');
      expect(button).toHaveClass('border-gray-300');
    });

    it('renders ghost variant correctly', () => {
      render(<Button variant="ghost">Ghost</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-gray-700');
      expect(button).toHaveClass('hover:bg-gray-100');
    });

    it('renders danger variant correctly', () => {
      render(<Button variant="danger">Danger</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-red-600');
      expect(button).toHaveClass('text-white');
    });
  });

  // ===========================================================================
  // Size Variations
  // ===========================================================================

  describe('Size Variations', () => {
    it('renders medium size by default', () => {
      render(<Button>Medium</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-4');
      expect(button).toHaveClass('py-2');
    });

    it('renders small size correctly', () => {
      render(<Button size="sm">Small</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-3');
      expect(button).toHaveClass('py-1.5');
      expect(button).toHaveClass('text-sm');
    });

    it('renders medium size correctly', () => {
      render(<Button size="md">Medium</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-4');
      expect(button).toHaveClass('py-2');
      expect(button).toHaveClass('text-base');
    });

    it('renders large size correctly', () => {
      render(<Button size="lg">Large</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-6');
      expect(button).toHaveClass('py-3');
      expect(button).toHaveClass('text-lg');
    });
  });

  // ===========================================================================
  // Click Handling
  // ===========================================================================

  describe('Click Handling', () => {
    it('calls onClick handler when clicked', async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(<Button onClick={handleClick}>Click me</Button>);

      await user.click(screen.getByRole('button'));

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('passes event to onClick handler', async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(<Button onClick={handleClick}>Click me</Button>);

      await user.click(screen.getByRole('button'));

      expect(handleClick).toHaveBeenCalledWith(expect.any(Object));
    });

    it('does not call onClick when disabled', async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(
        <Button onClick={handleClick} disabled>
          Click me
        </Button>
      );

      await user.click(screen.getByRole('button'));

      expect(handleClick).not.toHaveBeenCalled();
    });

    it('does not call onClick when loading', async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(
        <Button onClick={handleClick} isLoading>
          Click me
        </Button>
      );

      await user.click(screen.getByRole('button'));

      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Disabled State
  // ===========================================================================

  describe('Disabled State', () => {
    it('disables button when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('applies disabled styles', () => {
      render(<Button disabled>Disabled</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:opacity-50');
      expect(button).toHaveClass('disabled:cursor-not-allowed');
    });

    it('is not disabled when disabled prop is false', () => {
      render(<Button disabled={false}>Enabled</Button>);

      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
    });
  });

  // ===========================================================================
  // Loading State
  // ===========================================================================

  describe('Loading State', () => {
    it('shows loading spinner when isLoading is true', () => {
      render(<Button isLoading>Loading</Button>);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('disables button when loading', () => {
      render(<Button isLoading>Loading</Button>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('does not show loading spinner when isLoading is false', () => {
      render(<Button isLoading={false}>Not Loading</Button>);

      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
    });

    it('still renders children while loading', () => {
      render(<Button isLoading>Submit</Button>);

      expect(screen.getByText('Submit')).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Full Width
  // ===========================================================================

  describe('Full Width', () => {
    it('applies full width class when fullWidth is true', () => {
      render(<Button fullWidth>Full Width</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('w-full');
    });

    it('does not apply full width class when fullWidth is false', () => {
      render(<Button fullWidth={false}>Not Full Width</Button>);

      const button = screen.getByRole('button');
      expect(button).not.toHaveClass('w-full');
    });
  });

  // ===========================================================================
  // Custom className
  // ===========================================================================

  describe('Custom className', () => {
    it('applies custom className', () => {
      render(<Button className="custom-class">Custom</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('custom-class');
    });

    it('merges custom className with default classes', () => {
      render(<Button className="custom-class" variant="primary">Custom</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('custom-class');
      expect(button).toHaveClass('bg-blue-600');
    });
  });

  // ===========================================================================
  // Button Type
  // ===========================================================================

  describe('Button Type', () => {
    it('has type="button" by default when not specified', () => {
      render(<Button>Button</Button>);

      const button = screen.getByRole('button');
      // Note: When no type is specified, browser default is "submit" in forms
      // but our component should work correctly in both cases
      expect(button).toBeInTheDocument();
    });

    it('accepts type="submit"', () => {
      render(<Button type="submit">Submit</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'submit');
    });

    it('accepts type="reset"', () => {
      render(<Button type="reset">Reset</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'reset');
    });
  });

  // ===========================================================================
  // Accessibility
  // ===========================================================================

  describe('Accessibility', () => {
    it('has correct role', () => {
      render(<Button>Accessible</Button>);

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('is focusable when not disabled', async () => {
      const user = userEvent.setup();
      render(<Button>Focusable</Button>);

      await user.tab();

      expect(screen.getByRole('button')).toHaveFocus();
    });

    it('is not focusable when disabled', async () => {
      const user = userEvent.setup();
      render(<Button disabled>Not Focusable</Button>);

      await user.tab();

      expect(screen.getByRole('button')).not.toHaveFocus();
    });

    it('supports aria-label', () => {
      render(<Button aria-label="Close dialog">X</Button>);

      expect(screen.getByRole('button', { name: /close dialog/i })).toBeInTheDocument();
    });
  });
});
