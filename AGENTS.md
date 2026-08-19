# ChargeGrid Intelligence — Agent Instructions

## Mission

Build and maintain the ChargeGrid Intelligence MVP described in:

1. `SPEC.md`
2. `BRIEFING.md`

`SPEC.md` is the implementation source of truth.

If requirements conflict:

```text
SPEC.md
>
BRIEFING.md
>
README.md
>
existing implementation
```

Do not silently invent new business rules.

---

# Before Making Changes

Before implementing a task:

1. read the relevant sections of `SPEC.md`;
2. inspect the existing implementation;
3. inspect existing tests;
4. identify the smallest coherent change;
5. preserve existing working behavior unless the task explicitly changes it.

Do not assume a module is missing until you inspect the repository.

---

# Development Priorities

Use this priority order:

```text
correctness
>
simplicity
>
testability
>
maintainability
>
optimization
```

Prefer explicit, understandable code over clever abstractions.

This is an academic MVP that must be easy to demonstrate and explain.

---

# Architecture

The application is a:

> **modular monolith**

Do not convert it into microservices.

Expected major areas:

```text
backend
frontend
simulation
energy management
billing
analytics
machine learning
```

Keep module boundaries clear without introducing unnecessary infrastructure.

---

# Approved Stack

## Backend

```text
Python 3.12
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
PostgreSQL
Pytest
```

## Frontend

```text
React
TypeScript
Vite
React Router
Tailwind CSS
Recharts
Vitest
React Testing Library
```

## Data / ML

```text
Pandas
NumPy
Scikit-learn
Joblib
```

## Environment

```text
Docker
Docker Compose
```

Do not replace major technologies unless explicitly requested.

---

# Do Not Introduce

Unless explicitly required by a task, do not add:

```text
microservices
Kubernetes
Kafka
RabbitMQ
Redis
Celery
GraphQL
CQRS
event sourcing
Terraform
Deep Learning
LLM features
vector databases
payment gateways
mobile native applications
```

Avoid speculative infrastructure.

---

# Business Rules

Business rules belong primarily in service/domain code.

Do not hide critical rules inside:

* route handlers;
* React components;
* database models;
* background scripts.

Critical rules include:

* charging session state transitions;
* power allocation;
* grid limits;
* solar allocation;
* energy calculation;
* billing;
* ESG calculations;
* peak-risk classification.

---

# Energy Safety Invariants

Never introduce code that can intentionally violate:

```text
allocated_power_kw >= 0
```

```text
allocated_power_kw <= requested_power_kw
```

```text
allocated_power_kw <= charger.max_power_kw
```

```text
allocated_power_kw <= vehicle.max_charge_power_kw
```

```text
total_grid_power_kw <= grid_limit_kw
```

Machine Learning predictions must never override these constraints.

---

# Machine Learning

ML is advisory.

It may:

* predict demand;
* classify peak risk;
* generate deterministic recommendations.

It must not directly override deterministic energy constraints.

Always retain a baseline for comparison.

Always report evaluation metrics for trained models.

Prevent temporal data leakage.

Do not introduce Deep Learning for the MVP.

---

# Database Rules

Use Alembic migrations for schema changes.

Do not rely on manual database modification.

Use UUID identifiers.

Store timestamps in UTC.

Use decimal-safe types for monetary values.

Never store plaintext passwords.

---

# API Rules

All public API routes belong under:

```text
/api/v1
```

Use Pydantic schemas for request and response validation.

Use appropriate HTTP status codes.

Avoid exposing internal stack traces.

Keep OpenAPI generation working.

---

# Frontend Rules

Use TypeScript.

Avoid `any` unless there is a concrete reason.

Keep API calls outside presentation components when practical.

Prefer reusable components for:

* KPI cards;
* charts;
* tables;
* alerts;
* forms.

Do not duplicate business formulas in the frontend when the backend is their source of truth.

---

# Testing

Every change to critical business logic must include or update tests.

Prioritize tests for:

1. power allocation;
2. grid limits;
3. solar allocation;
4. energy calculations;
5. billing;
6. session transitions;
7. peak-risk classification;
8. API behavior.

Bug fixes should include a regression test whenever practical.

---

# Required Validation

Before considering a task complete, run the relevant available checks.

Examples:

```text
backend tests
frontend tests
type checking
linting
build
```

Do not claim a command passed unless it was actually executed successfully.

If a required tool or dependency prevents a test from running, report that explicitly.

---

# Definition of Done

A task is complete only when applicable items are satisfied:

* implementation is complete;
* requirements in `SPEC.md` are respected;
* tests are added or updated;
* existing relevant tests pass;
* migrations exist for schema changes;
* frontend/backend integration works;
* errors are handled;
* documentation is updated when behavior changes;
* no secrets were introduced.

---

# Scope Discipline

Before adding a feature, ask:

> Is this required by `SPEC.md` or by the current task?

If not, do not implement it merely because it may be useful later.

Prefer TODO/documentation for future ideas instead of premature implementation.

---

# Refactoring

Refactor when it:

* removes duplication;
* clarifies business logic;
* improves testability;
* fixes an architectural violation;
* directly supports the requested feature.

Avoid broad unrelated refactors during feature work.

---

# Dependencies

Before adding a dependency:

1. verify the existing stack cannot reasonably solve the problem;
2. prefer mature and minimal dependencies;
3. avoid adding a library for trivial functionality.

Do not change framework choices without explicit instruction.

---

# Error Handling

Expected domain errors should be handled explicitly.

Examples:

```text
charger unavailable
vehicle not owned by user
session already active
invalid session transition
resource not found
energy constraint conflict
```

Do not silently ignore failures.

---

# Security

Never commit:

```text
.env
passwords
tokens
API keys
private keys
credentials
```

Use environment variables.

Never expose password hashes or sensitive authentication information through API responses.

---

# Simulation

Keep simulation code isolated from core business rules.

The simulator is a data source, not the owner of the business domain.

Prefer interfaces that make future replacement possible without implementing future hardware integrations now.

---

# Documentation

When changing a fundamental rule, update the relevant source:

```text
SPEC.md
README.md
code comments
```

Do not duplicate large sections of documentation across multiple files.

Keep this `AGENTS.md` operational and concise.

---

# Working Style

For substantial changes:

1. inspect;
2. plan;
3. implement the smallest coherent vertical slice;
4. test;
5. review the diff;
6. fix regressions;
7. summarize what changed.

Prefer completing one working end-to-end flow over leaving several partially implemented layers.

---

# Golden Path

The most important product flow is:

```text
start charging session
        ↓
calculate requested power
        ↓
allocate available power
        ↓
prioritize solar
        ↓
record energy
        ↓
predict demand
        ↓
show alerts
        ↓
finish session
        ↓
calculate billing and ESG
        ↓
update dashboard
```

Changes affecting this flow require particular care and regression testing.

---

# Final Principle

When choosing between:

```text
more sophisticated
```

and:

```text
simpler, correct, testable and demonstrable
```

choose the second option.
