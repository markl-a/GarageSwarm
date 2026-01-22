import React, { useMemo } from 'react';

interface PasswordStrengthProps {
  password: string;
  showRequirements?: boolean;
}

interface Requirement {
  id: string;
  label: string;
  test: (password: string) => boolean;
}

const requirements: Requirement[] = [
  {
    id: 'length',
    label: 'At least 8 characters',
    test: (password) => password.length >= 8,
  },
  {
    id: 'uppercase',
    label: 'At least one uppercase letter',
    test: (password) => /[A-Z]/.test(password),
  },
  {
    id: 'lowercase',
    label: 'At least one lowercase letter',
    test: (password) => /[a-z]/.test(password),
  },
  {
    id: 'number',
    label: 'At least one number',
    test: (password) => /\d/.test(password),
  },
  {
    id: 'special',
    label: 'At least one special character (!@#$%^&*)',
    test: (password) => /[!@#$%^&*(),.?":{}|<>]/.test(password),
  },
];

export function PasswordStrength({ password, showRequirements = true }: PasswordStrengthProps) {
  const analysis = useMemo(() => {
    const passed = requirements.filter((req) => req.test(password));
    const score = passed.length;

    let strength: 'weak' | 'fair' | 'good' | 'strong' = 'weak';
    let color = 'bg-red-500';
    let textColor = 'text-red-500';

    if (score === 0) {
      strength = 'weak';
      color = 'bg-slate-600';
      textColor = 'text-slate-400';
    } else if (score <= 2) {
      strength = 'weak';
      color = 'bg-red-500';
      textColor = 'text-red-500';
    } else if (score <= 3) {
      strength = 'fair';
      color = 'bg-yellow-500';
      textColor = 'text-yellow-500';
    } else if (score <= 4) {
      strength = 'good';
      color = 'bg-blue-500';
      textColor = 'text-blue-500';
    } else {
      strength = 'strong';
      color = 'bg-green-500';
      textColor = 'text-green-500';
    }

    return {
      score,
      strength,
      color,
      textColor,
      passed,
      percentage: (score / requirements.length) * 100,
    };
  }, [password]);

  if (!password) {
    return null;
  }

  return (
    <div className="mt-2 space-y-3">
      {/* Strength Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Password strength</span>
          <span className={`font-medium capitalize ${analysis.textColor}`}>
            {analysis.strength}
          </span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${analysis.color}`}
            style={{ width: `${analysis.percentage}%` }}
          />
        </div>
      </div>

      {/* Requirements Checklist */}
      {showRequirements && (
        <div className="space-y-1.5">
          {requirements.map((req) => {
            const passed = req.test(password);
            return (
              <div
                key={req.id}
                className={`flex items-center gap-2 text-xs transition-colors ${
                  passed ? 'text-green-400' : 'text-slate-500'
                }`}
              >
                {passed ? (
                  <svg
                    className="w-3.5 h-3.5 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-3.5 h-3.5 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                )}
                <span>{req.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Utility function to check if password meets minimum requirements
export function isPasswordValid(password: string): boolean {
  return requirements.every((req) => req.test(password));
}

// Utility function to get password strength score (0-5)
export function getPasswordScore(password: string): number {
  return requirements.filter((req) => req.test(password)).length;
}
