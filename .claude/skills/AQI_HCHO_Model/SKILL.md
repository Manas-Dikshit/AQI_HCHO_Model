```markdown
# AQI_HCHO_Model Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `AQI_HCHO_Model` Python repository. The codebase focuses on modeling Air Quality Index (AQI) and formaldehyde (HCHO) concentrations, with an emphasis on clean code practices, conventional commits, and structured testing. No external frameworks are required, making it lightweight and easy to extend.

## Coding Conventions

### File Naming
- Use **snake_case** for all file and module names.
  - Example: `data_loader.py`, `model_trainer.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import preprocess_data
    ```

### Export Style
- Use **named exports** (explicit function and class definitions).
  - Example:
    ```python
    def train_model(...):
        ...
    ```

### Commit Messages
- Follow **Conventional Commits** with these prefixes:
  - `docs`: Documentation changes
  - `feat`: New features
  - `style`: Code style or formatting changes
- Keep commit messages concise (average ~69 characters).
  - Example:
    ```
    feat: add HCHO concentration prediction module
    ```

## Workflows

### Adding a New Feature
**Trigger:** When implementing new functionality  
**Command:** `/add-feature`

1. Create a new Python file using snake_case if needed.
2. Implement the feature with named functions/classes.
3. Use relative imports for internal modules.
4. Write or update tests in a corresponding `*.test.*` file.
5. Commit changes using the `feat:` prefix.
    ```
    git commit -m "feat: implement [feature description]"
    ```

### Improving Documentation
**Trigger:** When updating or adding documentation  
**Command:** `/update-docs`

1. Edit or create documentation files as needed.
2. Commit changes using the `docs:` prefix.
    ```
    git commit -m "docs: update [doc section]"
    ```

### Refactoring or Styling Code
**Trigger:** When making non-functional code improvements  
**Command:** `/style-update`

1. Refactor code for readability or consistency.
2. Ensure file and import naming conventions are followed.
3. Commit changes using the `style:` prefix.
    ```
    git commit -m "style: refactor [module or function]"
    ```

### Running Tests
**Trigger:** To verify code correctness  
**Command:** `/run-tests`

1. Identify test files matching the `*.test.*` pattern.
2. Run tests using your preferred Python test runner (e.g., `pytest`, `unittest`).
    ```
    pytest
    ```
    or
    ```
    python -m unittest discover
    ```

## Testing Patterns

- Test files follow the `*.test.*` naming pattern (e.g., `model.test.py`).
- Testing framework is not specified; use standard Python test tools like `pytest` or `unittest`.
- Place test functions/classes in the corresponding test files.

  Example (`model.test.py`):
  ```python
  import unittest
  from .model_trainer import train_model

  class TestModelTrainer(unittest.TestCase):
      def test_train_model_output(self):
          result = train_model(...)
          self.assertIsNotNone(result)
  ```

## Commands
| Command        | Purpose                                |
|----------------|----------------------------------------|
| /add-feature   | Add a new feature or module            |
| /update-docs   | Update or add documentation            |
| /style-update  | Refactor or restyle code               |
| /run-tests     | Run all test files                     |
```
