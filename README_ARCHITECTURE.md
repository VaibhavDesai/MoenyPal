# MoneyPal Architecture

## Overview
MoneyPal follows an MVC (Model-View-Controller) architecture pattern to maintain clean separation of concerns and improve code maintainability.

## Directory Structure

```
MoneyPal/
├── app.py                 # Main entry point (thin orchestrator)
├── models/                # Data layer (database & business logic)
│   ├── __init__.py
│   ├── database.py       # Database connection & initialization
│   ├── expense.py        # Expense CRUD operations
│   ├── settings.py       # Settings management
│   ├── tags.py           # Tag management
│   └── analytics.py      # Analytics data aggregation
├── views/                 # Presentation layer (UI components)
│   ├── __init__.py
│   ├── navigation.py     # Bottom navigation bar
│   ├── dashboard.py      # Dashboard tab view
│   ├── add.py            # Add expense tab view
│   ├── transactions.py   # Transactions tab view
│   ├── analytics.py      # Analytics tab view
│   └── settings.py       # Settings tab view
├── utils/                 # Shared utilities
│   ├── __init__.py
│   ├── constants.py      # Application constants
│   └── helpers.py        # Helper functions
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Architecture Layers

### 1. Models Layer (`models/`)
Handles all data persistence and business logic:
- **database.py**: SQLAlchemy engine setup, database initialization, SQLite optimizations (WAL mode, retry logic)
- **expense.py**: Expense CRUD operations (create, read, update, delete, list with filters)
- **settings.py**: Application settings management (income, budgets, savings goals)
- **tags.py**: Tag management (create, normalize, link to expenses)
- **analytics.py**: Data aggregation for charts (monthly/weekly totals, category breakdowns)

### 2. Views Layer (`views/`)
Contains all UI components and rendering logic:
- **navigation.py**: Fixed bottom navigation bar with mobile-optimized styling
- **dashboard.py**: Budget overview, spending pie chart, category progress bars
- **add.py**: Quick expense entry form with tags
- **transactions.py**: Transaction list with search, filters, edit/delete functionality
- **analytics.py**: Plotly charts for spending trends
- **settings.py**: Income/budget configuration, data export, reset functionality

### 3. Utils Layer (`utils/`)
Shared utilities and constants:
- **constants.py**: Categories, labels, tab definitions
- **helpers.py**: Formatting functions, date parsing, display helpers

### 4. Controller Layer (`app.py`)
Thin orchestrator that:
- Initializes the database
- Routes requests to appropriate views based on query parameters
- Manages the application lifecycle

## Data Flow

```
User Interaction
    ↓
View (Streamlit UI)
    ↓
Model (Database Operations)
    ↓
SQLite Database
```

## Key Design Decisions

1. **MVC Pattern**: Clear separation between data (models), presentation (views), and routing (controller)
2. **Tab-based Organization**: Each tab has its own view module for maintainability
3. **Reusable Models**: Database operations are centralized and can be called from any view
4. **SQLite Optimizations**: WAL mode, busy timeout, and retry logic for concurrent access
5. **Mobile-First**: All views are optimized for mobile rendering with responsive layouts

## Adding New Features

### To add a new tab:
1. Create a new view module in `views/` (e.g., `views/reports.py`)
2. Add the tab definition to `utils/constants.py` in the `TABS` list
3. Import and route to the view in `app.py`'s `main()` function

### To add new data operations:
1. Add the function to the appropriate model (e.g., `models/expense.py`)
2. Export it in `models/__init__.py`
3. Import and use it in the relevant view

### To add new utilities:
1. Add the function to `utils/helpers.py` or create a new utility module
2. Export it in `utils/__init__.py`
3. Import where needed

## Database Schema

### Tables:
- **expenses**: Core transaction data (id, amount_cents, category, note, occurred_at, created_at)
- **tags**: Tag definitions (id, name)
- **expense_tags**: Many-to-many relationship (expense_id, tag_id)
- **settings**: Application settings (income, budgets, savings goal)

## Benefits of This Architecture

1. **Maintainability**: Each component has a single responsibility
2. **Testability**: Models can be tested independently of UI
3. **Scalability**: Easy to add new features without affecting existing code
4. **Readability**: Clear structure makes it easy to find and understand code
5. **Reusability**: Models and utilities can be shared across views
