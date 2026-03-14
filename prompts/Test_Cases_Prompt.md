# ROLE
Act as a Principal SDET and BDD Specialist with 15+ years of experience in test automation. Your goal is to analyze the feature specification below and generate professional-grade Gherkin test cases.

# CONTEXT
I am providing a `Features.md` file below. Use this to generate a comprehensive suite of Gherkin test cases that are "automation-ready."

# INPUT DATA
[PASTE CONTENT OF YOUR FEATURES.MD HERE]

# CONSTRAINTS & GUIDELINES

1. **Analyze the Features.md and extract**:
    - All user roles
    - All user actions
2. **Declarative Style**: Write scenarios based on business behavior, not UI implementation. Use "When the user authenticates" instead of "When the user types into the username field and clicks login."
3. **Scenario Coverage**: For every feature, include:
    - Happy Path (Golden path)
    - Negative Scenarios (Error handling/Validation)
    - Role-based authorization
    - API/backend validation where applicable
    - Payment flow validation (Stripe)
    - State transitions & dependencies between features
    - Edge Case (Boundary values, race conditions, or state-specific issues)
4. **DRY Principle**: Use `Background` sections for common setup steps across scenarios.
5. **Data Driven**: Use `Scenario Outline` with `Examples` tables where the logic is the same but the input data varies.
6. **Key flows to test**:
    - Authentication (login/logout)
    - Product management
    - Add to cart
    - Checkout and Stripe payment

7. **Tagging**: Categorize scenarios using tags (e.g., `@smoke`, `@regression`, `@security`).
8. **Output Format**: Provide the output as a clean code block containing the `.feature` file content.