# Testing Pyramid Strategy

This project adheres to a strict testing pyramid. All agents must enforce the following distribution and methodology:

## Distribution
- **60% Unit Tests**: Focus on isolated business logic, models, services, and isolated components. (Tool: **Pest**)
- **30% Feature/Integration Tests**: Focus on API endpoints, controller responses, and database interactions. (Tool: **Pest**)
- **10% E2E Tests**: Focus on critical member/admin journeys (e.g., Member Registration, Booking flow, Admin settings). (Tool: **Laravel Dusk**)

## Methodology
- **Test-Driven Development (TDD)** is MANDATORY for bug fixes. Before fixing a bug, write a failing test that reproduces the bug, then write the code to pass the test.
- Every new feature MUST include the appropriate tests according to the pyramid distribution.
- Tests must not reintroduce member-core radiography upload, image processing, AI job dispatch, mock diagnosis, or active walk-in creation endpoints unless the PRD is explicitly revised.

## Commands
- Run Unit/Feature tests: `./vendor/bin/pest`
- Run E2E tests: `php artisan dusk`
