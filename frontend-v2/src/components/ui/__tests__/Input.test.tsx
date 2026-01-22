/**
 * Input Component Tests
 *
 * Tests for the Input UI component covering:
 * - Value changes
 * - Error state
 * - Label rendering
 * - Helper text
 * - Accessibility
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../Input';

describe('Input Component', () => {
  // ===========================================================================
  // Basic Rendering
  // ===========================================================================

  describe('Basic Rendering', () => {
    it('renders input element', () => {
      render(<Input aria-label="Test input" />);

      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('forwards ref correctly', () => {
      const ref = vi.fn();
      render(<Input ref={ref} aria-label="Test input" />);

      expect(ref).toHaveBeenCalled();
    });

    it('spreads additional props to input element', () => {
      render(<Input data-testid="custom-input" placeholder="Enter text" aria-label="Test" />);

      const input = screen.getByTestId('custom-input');
      expect(input).toHaveAttribute('placeholder', 'Enter text');
    });

    it('applies custom className', () => {
      render(<Input className="custom-class" aria-label="Test input" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('custom-class');
    });
  });

  // ===========================================================================
  // Label Rendering
  // ===========================================================================

  describe('Label Rendering', () => {
    it('renders label when provided', () => {
      render(<Input label="Email Address" />);

      expect(screen.getByText('Email Address')).toBeInTheDocument();
    });

    it('associates label with input via htmlFor/id', () => {
      render(<Input label="Email Address" />);

      const input = screen.getByLabelText('Email Address');
      expect(input).toBeInTheDocument();
    });

    it('uses custom id when provided', () => {
      render(<Input label="Email Address" id="custom-email-id" />);

      const input = screen.getByLabelText('Email Address');
      expect(input).toHaveAttribute('id', 'custom-email-id');
    });

    it('generates id from label when id not provided', () => {
      render(<Input label="Email Address" />);

      const input = screen.getByLabelText('Email Address');
      expect(input).toHaveAttribute('id', 'email-address');
    });

    it('does not render label when not provided', () => {
      render(<Input aria-label="Test input" />);

      expect(screen.queryByRole('label')).not.toBeInTheDocument();
    });

    it('applies correct label styling', () => {
      render(<Input label="Email Address" />);

      const label = screen.getByText('Email Address');
      expect(label).toHaveClass('text-sm');
      expect(label).toHaveClass('font-medium');
    });
  });

  // ===========================================================================
  // Value Changes
  // ===========================================================================

  describe('Value Changes', () => {
    it('displays initial value', () => {
      render(<Input defaultValue="Initial Value" aria-label="Test" />);

      expect(screen.getByRole('textbox')).toHaveValue('Initial Value');
    });

    it('updates value on user input', async () => {
      const user = userEvent.setup();
      render(<Input aria-label="Test input" />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'New value');

      expect(input).toHaveValue('New value');
    });

    it('calls onChange handler when value changes', async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(<Input onChange={handleChange} aria-label="Test input" />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'a');

      expect(handleChange).toHaveBeenCalled();
    });

    it('passes event to onChange handler', async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      render(<Input onChange={handleChange} aria-label="Test input" />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'a');

      expect(handleChange).toHaveBeenCalledWith(
        expect.objectContaining({
          target: expect.objectContaining({ value: 'a' }),
        })
      );
    });

    it('works as controlled input', async () => {
      const handleChange = vi.fn();
      const user = userEvent.setup();

      const { rerender } = render(
        <Input value="controlled" onChange={handleChange} aria-label="Test input" />
      );

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('controlled');

      // Type should trigger onChange
      await user.type(input, 'x');
      expect(handleChange).toHaveBeenCalled();

      // Value should remain controlled
      expect(input).toHaveValue('controlled');

      // Update controlled value
      rerender(<Input value="updated" onChange={handleChange} aria-label="Test input" />);
      expect(input).toHaveValue('updated');
    });
  });

  // ===========================================================================
  // Error State
  // ===========================================================================

  describe('Error State', () => {
    it('displays error message when provided', () => {
      render(<Input error="This field is required" label="Email" />);

      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    it('displays error message with alert role', () => {
      render(<Input error="Invalid email" label="Email" />);

      expect(screen.getByRole('alert')).toHaveTextContent('Invalid email');
    });

    it('applies error styling to input', () => {
      render(<Input error="Error" label="Email" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('border-red-300');
    });

    it('sets aria-invalid to true when error is present', () => {
      render(<Input error="Error" label="Email" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('sets aria-invalid to false when no error', () => {
      render(<Input label="Email" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'false');
    });

    it('links error message via aria-describedby', () => {
      render(<Input error="Invalid email format" label="Email" />);

      const input = screen.getByRole('textbox');
      const errorId = input.getAttribute('aria-describedby');

      expect(errorId).toBeTruthy();
      expect(screen.getByText('Invalid email format')).toHaveAttribute('id', errorId);
    });

    it('applies error text styling', () => {
      render(<Input error="Error message" label="Email" />);

      const errorText = screen.getByText('Error message');
      expect(errorText).toHaveClass('text-red-600');
      expect(errorText).toHaveClass('text-sm');
    });
  });

  // ===========================================================================
  // Helper Text
  // ===========================================================================

  describe('Helper Text', () => {
    it('displays helper text when provided', () => {
      render(<Input helperText="Enter your email address" label="Email" />);

      expect(screen.getByText('Enter your email address')).toBeInTheDocument();
    });

    it('links helper text via aria-describedby', () => {
      render(<Input helperText="Helpful hint" label="Email" />);

      const input = screen.getByRole('textbox');
      const helperId = input.getAttribute('aria-describedby');

      expect(helperId).toBeTruthy();
      expect(screen.getByText('Helpful hint')).toHaveAttribute('id', helperId);
    });

    it('applies helper text styling', () => {
      render(<Input helperText="Helper text" label="Email" />);

      const helperText = screen.getByText('Helper text');
      expect(helperText).toHaveClass('text-gray-500');
      expect(helperText).toHaveClass('text-sm');
    });

    it('does not display helper text when error is present', () => {
      render(
        <Input
          error="Error message"
          helperText="This should not appear"
          label="Email"
        />
      );

      expect(screen.queryByText('This should not appear')).not.toBeInTheDocument();
      expect(screen.getByText('Error message')).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Input Types
  // ===========================================================================

  describe('Input Types', () => {
    it('defaults to text type', () => {
      render(<Input aria-label="Test" />);

      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'text');
    });

    it('accepts email type', () => {
      render(<Input type="email" aria-label="Email" />);

      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'email');
    });

    it('accepts password type', () => {
      render(<Input type="password" aria-label="Password" />);

      // Password inputs don't have textbox role
      expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
    });

    it('accepts number type', () => {
      render(<Input type="number" aria-label="Number" />);

      expect(screen.getByRole('spinbutton')).toHaveAttribute('type', 'number');
    });

    it('accepts tel type', () => {
      render(<Input type="tel" aria-label="Phone" />);

      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'tel');
    });
  });

  // ===========================================================================
  // Disabled State
  // ===========================================================================

  describe('Disabled State', () => {
    it('disables input when disabled prop is true', () => {
      render(<Input disabled aria-label="Test" />);

      expect(screen.getByRole('textbox')).toBeDisabled();
    });

    it('does not update value when disabled', async () => {
      const user = userEvent.setup();
      render(<Input disabled defaultValue="Original" aria-label="Test" />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'New');

      expect(input).toHaveValue('Original');
    });
  });

  // ===========================================================================
  // Required State
  // ===========================================================================

  describe('Required State', () => {
    it('marks input as required when required prop is true', () => {
      render(<Input required aria-label="Test" />);

      expect(screen.getByRole('textbox')).toBeRequired();
    });

    it('does not mark input as required when required prop is false', () => {
      render(<Input required={false} aria-label="Test" />);

      expect(screen.getByRole('textbox')).not.toBeRequired();
    });
  });

  // ===========================================================================
  // Read Only State
  // ===========================================================================

  describe('Read Only State', () => {
    it('marks input as readonly when readOnly prop is true', () => {
      render(<Input readOnly aria-label="Test" />);

      expect(screen.getByRole('textbox')).toHaveAttribute('readonly');
    });

    it('does not allow editing when readonly', async () => {
      const user = userEvent.setup();
      render(<Input readOnly defaultValue="Read only" aria-label="Test" />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'New');

      expect(input).toHaveValue('Read only');
    });
  });

  // ===========================================================================
  // Placeholder
  // ===========================================================================

  describe('Placeholder', () => {
    it('displays placeholder text', () => {
      render(<Input placeholder="Enter email..." aria-label="Email" />);

      expect(screen.getByPlaceholderText('Enter email...')).toBeInTheDocument();
    });

    it('clears placeholder when user types', async () => {
      const user = userEvent.setup();
      render(<Input placeholder="Type here..." aria-label="Test" />);

      const input = screen.getByPlaceholderText('Type here...');
      await user.type(input, 'Hello');

      expect(input).toHaveValue('Hello');
      // Placeholder is still there, just hidden by value
      expect(input).toHaveAttribute('placeholder', 'Type here...');
    });
  });

  // ===========================================================================
  // Accessibility
  // ===========================================================================

  describe('Accessibility', () => {
    it('is focusable', async () => {
      const user = userEvent.setup();
      render(<Input aria-label="Test input" />);

      await user.tab();

      expect(screen.getByRole('textbox')).toHaveFocus();
    });

    it('is not focusable when disabled', async () => {
      const user = userEvent.setup();
      render(<Input disabled aria-label="Test input" />);

      await user.tab();

      expect(screen.getByRole('textbox')).not.toHaveFocus();
    });

    it('supports aria-label', () => {
      render(<Input aria-label="Custom label" />);

      expect(screen.getByRole('textbox', { name: 'Custom label' })).toBeInTheDocument();
    });

    it('supports autocomplete attribute', () => {
      render(<Input autoComplete="email" aria-label="Email" />);

      expect(screen.getByRole('textbox')).toHaveAttribute('autocomplete', 'email');
    });
  });

  // ===========================================================================
  // Focus and Blur
  // ===========================================================================

  describe('Focus and Blur', () => {
    it('calls onFocus when focused', async () => {
      const handleFocus = vi.fn();
      const user = userEvent.setup();

      render(<Input onFocus={handleFocus} aria-label="Test" />);

      await user.click(screen.getByRole('textbox'));

      expect(handleFocus).toHaveBeenCalled();
    });

    it('calls onBlur when blurred', async () => {
      const handleBlur = vi.fn();
      const user = userEvent.setup();

      render(<Input onBlur={handleBlur} aria-label="Test" />);

      const input = screen.getByRole('textbox');
      await user.click(input);
      await user.tab();

      expect(handleBlur).toHaveBeenCalled();
    });
  });
});
