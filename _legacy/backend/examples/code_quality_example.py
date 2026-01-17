"""
Code Quality Evaluator Usage Examples

This file demonstrates various use cases for the real CodeQualityEvaluator.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evaluators.code_quality import CodeQualityEvaluator


# Sample code snippets for testing
GOOD_CODE = '''
def calculate_area(width: float, height: float) -> float:
    """
    Calculate the area of a rectangle.

    Args:
        width: The width of the rectangle
        height: The height of the rectangle

    Returns:
        The calculated area
    """
    return width * height


def calculate_perimeter(width: float, height: float) -> float:
    """
    Calculate the perimeter of a rectangle.

    Args:
        width: The width of the rectangle
        height: The height of the rectangle

    Returns:
        The calculated perimeter
    """
    return 2 * (width + height)
'''

BAD_CODE = '''
def bad_function(x,y,z):
    if x>0:
        if y>0:
            if z>0:
                if x>y:
                    if y>z:
                        if x>z:
                            result=x+y+z
                            really_long_variable_name_that_exceeds_the_maximum_line_length_of_120_characters_and_should_trigger_a_warning = result
                            return really_long_variable_name_that_exceeds_the_maximum_line_length_of_120_characters_and_should_trigger_a_warning
    return 0
'''

SYNTAX_ERROR_CODE = '''
def broken_function()
    print("Missing colon")
    return 42
'''


async def example_1_basic_usage():
    """Example 1: Basic usage with default configuration"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    evaluator = CodeQualityEvaluator()

    print(f"Tools available: {evaluator._tools_available}")
    print()

    result = await evaluator.evaluate(GOOD_CODE, {"language": "python"})

    print(f"Score: {result.score}")
    print(f"Syntax errors: {result.details['syntax_errors']}")
    print(f"Lint warnings: {result.details['lint_warnings']}")
    print(f"Lint errors: {result.details['lint_errors']}")
    print(f"Comment coverage: {result.details['comment_coverage']}%")
    print(f"Tools used: {result.details['tools_used']}")
    print(f"Total issues: {len(result.issues)}")
    print()


async def example_2_problematic_code():
    """Example 2: Evaluating code with multiple issues"""
    print("=" * 60)
    print("Example 2: Problematic Code Analysis")
    print("=" * 60)

    evaluator = CodeQualityEvaluator()
    result = await evaluator.evaluate(BAD_CODE, {"language": "python"})

    print(f"Score: {result.score}")
    print(f"Issues found: {len(result.issues)}")
    print()

    print("Issues by severity:")
    severity_counts = {}
    for issue in result.issues:
        severity = issue.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    for severity, count in sorted(severity_counts.items()):
        print(f"  {severity}: {count}")
    print()

    print("Sample issues:")
    for i, issue in enumerate(result.issues[:5], 1):
        print(f"  {i}. Line {issue.get('line', '?')}: [{issue.get('severity')}] {issue.get('type')}")
        print(f"     {issue.get('message')}")
        print(f"     Source: {issue.get('source', 'unknown')}")
    print()

    if result.suggestions:
        print("Suggestions:")
        for i, suggestion in enumerate(result.suggestions[:5], 1):
            print(f"  {i}. {suggestion}")
    print()


async def example_3_syntax_error():
    """Example 3: Handling syntax errors"""
    print("=" * 60)
    print("Example 3: Syntax Error Handling")
    print("=" * 60)

    evaluator = CodeQualityEvaluator()
    result = await evaluator.evaluate(SYNTAX_ERROR_CODE, {"language": "python"})

    print(f"Score: {result.score}")
    print(f"Syntax errors: {result.details['syntax_errors']}")
    print()

    if result.issues:
        print("Syntax error details:")
        for issue in result.issues:
            if issue.get("type") == "syntax":
                print(f"  Line {issue.get('line', '?')}: {issue.get('message')}")
    print()


async def example_4_custom_config():
    """Example 4: Custom configuration"""
    print("=" * 60)
    print("Example 4: Custom Configuration")
    print("=" * 60)

    # Disable real tools (fallback to simulated)
    evaluator_simulated = CodeQualityEvaluator(
        config={"use_real_tools": False}
    )

    result_simulated = await evaluator_simulated.evaluate(BAD_CODE, {"language": "python"})

    print("Simulated mode:")
    print(f"  Score: {result_simulated.score}")
    print(f"  Tools used: {result_simulated.details['tools_used']}")
    print(f"  Issues: {len(result_simulated.issues)}")
    print()

    # Real tools with custom timeout
    evaluator_real = CodeQualityEvaluator(
        weight=1.5,
        config={
            "use_real_tools": True,
            "timeout": 60,
            "pylint_enabled": True,
            "flake8_enabled": True
        }
    )

    result_real = await evaluator_real.evaluate(BAD_CODE, {"language": "python"})

    print("Real tools mode:")
    print(f"  Score: {result_real.score}")
    print(f"  Tools used: {result_real.details['tools_used']}")
    print(f"  Issues: {len(result_real.issues)}")
    print()


async def example_5_compare_modes():
    """Example 5: Compare real vs simulated modes"""
    print("=" * 60)
    print("Example 5: Real vs Simulated Mode Comparison")
    print("=" * 60)

    test_code = '''
def test_function(a,b,c):
    result=a+b+c
    return result
'''

    # Simulated mode
    evaluator_sim = CodeQualityEvaluator(config={"use_real_tools": False})
    result_sim = await evaluator_sim.evaluate(test_code, {"language": "python"})

    # Real mode
    evaluator_real = CodeQualityEvaluator(config={"use_real_tools": True})
    result_real = await evaluator_real.evaluate(test_code, {"language": "python"})

    print("Comparison:")
    print(f"{'Metric':<25} {'Simulated':<15} {'Real':<15}")
    print("-" * 55)
    print(f"{'Score':<25} {float(result_sim.score):<15.1f} {float(result_real.score):<15.1f}")
    print(f"{'Issues found':<25} {len(result_sim.issues):<15} {len(result_real.issues):<15}")
    print(f"{'Lint warnings':<25} {result_sim.details['lint_warnings']:<15} {result_real.details['lint_warnings']:<15}")
    print(f"{'Tools used':<25} {str(result_sim.details['tools_used']):<15} {str(result_real.details['tools_used']):<15}")
    print()


async def example_6_complexity_analysis():
    """Example 6: Complexity analysis"""
    print("=" * 60)
    print("Example 6: Complexity Analysis")
    print("=" * 60)

    complex_code = '''
def highly_complex_function(a, b, c, d, e):
    """A function with high cyclomatic complexity"""
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return a + b + c + d + e
                    else:
                        return a + b + c + d
                else:
                    return a + b + c
            else:
                return a + b
        else:
            return a
    else:
        return 0


def simple_function(x, y):
    """A simple function with low complexity"""
    return x + y
'''

    evaluator = CodeQualityEvaluator()
    result = await evaluator.evaluate(complex_code, {"language": "python"})

    print(f"Score: {result.score}")
    print(f"High complexity functions: {result.details['high_complexity_count']}")
    print()

    print("Complexity details:")
    for detail in result.details.get("complexity_details", []):
        complexity = detail["complexity"]
        status = "HIGH" if complexity > 10 else "MODERATE" if complexity > 7 else "OK"
        print(f"  {detail['function']:<30} Complexity: {complexity:<3} [{status}]")
    print()

    # Show complexity-related issues
    complexity_issues = [i for i in result.issues if i.get("type") == "complexity"]
    if complexity_issues:
        print("Complexity issues:")
        for issue in complexity_issues:
            print(f"  Line {issue.get('line')}: {issue.get('message')}")
    print()


async def main():
    """Run all examples"""
    examples = [
        example_1_basic_usage,
        example_2_problematic_code,
        example_3_syntax_error,
        example_4_custom_config,
        example_5_compare_modes,
        example_6_complexity_analysis,
    ]

    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

        print()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
