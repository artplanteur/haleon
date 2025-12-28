# Detailed Application Technical Document: Haleon v1

This document provides a technical overview of the Haleon v1 application, based on an analysis of its codebase. It covers the high-level architecture, project structure, core functionalities like authentication and authorization, and key UI components.

## 1. Introduction

Haleon v1 is a Reflex-based single-page application designed with a modular structure. It features a central authentication and state management system that orchestrates access to various modular "applications" housed within the main framework. The user interface provides a persistent navigation bar and sidebar for overall application interaction.

## 2. High-Level Architecture

The application follows a client-server architecture typical of Reflex applications:
*   **Frontend (Client):** Built with the Reflex framework (Python compiled to web technologies), it handles the UI rendering, user interactions, and state management.
*   **Backend (Server):** Also written in Python, it manages application state, business logic, and interacts with the database.
*   **Database:** Uses SQLite (default `haleon.db`) with SQLAlchemy ORM via SQLModel for data persistence.

The core philosophy, as described in the `README.md`, is a "two-level" application: a parent UI manages user authentication and application access, while individual child applications reside in the `apps/` directory and leverage the parent's access levels.

## 3. Project Structure and Key Files

The project adheres to a clear directory structure to maintain separation of concerns:

*   **`haleon/`**: The main application source directory.
    *   **`haleon.py`**: The application's entry point. It defines Reflex routes for all pages (including admin panels), and initializes/seeds the database on startup. This file serves as a complete map of all pages in the application.
    *   **`apps/`**: Contains modular sub-applications (e.g., `OOB/`). Each sub-directory represents a distinct application with its own pages, state, and API logic.
    *   **`auth/`**: Manages authentication and authorization.
        *   **`auth_state.py`**: The central `AuthState` handles session management, the simulated SSO login flow, user state, and permissions. It also manages which applications are accessible.
        *   **`permissions.py`**: Defines the authorization logic, including `UserPermissions` (cascading user tiers) and `ApplicationPermissions` (explicit access grants).
    *   **`components/`**: Houses reusable UI components shared across the application.
        *   **`layout.py`**: The main UI shell that wraps every page. It calls `AuthState.load_user_from_session` on mount to restore user sessions. It assembles the navbar, sidebar, and main content area.
        *   **`navbar.py`**: The top navigation bar, featuring login triggers, dynamic application buttons based on user permissions, and user avatar.
        *   **`sidebar.py`**: The main navigation drawer, conditionally rendering admin links based on user permissions and displaying other settings.
        *   **`avatar.py`**: Implements the user avatar component, displaying user information and session details.
        *   **`footer.py`**: The application's footer component.
    *   **`db/`**: Contains all database-related logic.
        *   **`database.py`**: Configuration for the database connection.
        *   **`model/`**: SQLModel definitions for the database schema.
        *   **`crud/`**: Create, Read, Update, Delete (CRUD) operations for interacting with the database models.
        *   **`seed.py`**: Script for populating the database with initial data.
    *   **`pages/`**: Defines the main application pages.
        *   **`index.py`**: The initial landing page, handling routing for authenticated vs. unauthenticated users.
        *   **`home.py`**: The main authenticated home page.
        *   **`app_view.py`**: A dynamic page that loads and renders the content of specific modular applications based on the URL parameter.
        *   **`admin/`**: Contains UI and logic for the administration panels (e.g., `users.py`, `applications.py`, `access.py`).
    *   **`state/`**: Global state management (e.g., `i18n_state.py` for internationalization).
*   **`assets/`**: Static assets like CSS and images (`theme.css`).
*   **`data/`**: Stores the SQLite database file (`haleon.db`).
*   **`rxconfig.py`**: Reflex application configuration.
*   **`requirements.txt`**: Python dependencies.

## 4. Authentication & Authorization

### 4.1. Authentication Flow
Authentication is managed by the `AuthState` (`haleon/auth/auth_state.py`).
*   **SSO Simulation:** The `simulate_sso_login` function handles a simulated SSO process, creating or updating a user in the database.
*   **Session Management:** A `session_id` (a UUID) is generated upon login and stored in the browser's `rx.LocalStorage`. This `session_id` is then used by `AuthState.load_user_from_session` (called by the main `layout` component on every page mount) to restore the user's session and retrieve their details and permissions from the backend.
*   **Logout:** The `logout` function clears the session ID and resets the `AuthState`.

### 4.2. Authorization Levels (UserPermissions)
The application implements a three-tier cascading permission system defined in `haleon/auth/permissions.py` within the `UserPermissions` class:
*   **`is_active`**: The most basic level; the user account is active.
*   **`is_validated`**: The user account is validated (requires being active).
*   **`is_admin`**: The user has administrative privileges (requires being validated).

These levels are checked in a cascading manner: an admin must be validated, and a validated user must be active. This simplifies permission checks.

### 4.3. Application Access (ApplicationPermissions)
Access to modular applications (in `haleon/apps/`) is explicitly controlled via the `UserApplicationAccess` database table and enforced by `ApplicationPermissions.can_access_app`. A user *must* have an explicit entry in this table to access a given application. The `minimum_requirement` defined for an application (e.g., "validated", "admin") acts as a prerequisite for granting access, but does not automatically confer it.

## 5. Database and Data Model

The core database schema is defined using SQLModel in `haleon/db/model/`.

*   **`Users` (users.py):**
    *   `id`: Primary key.
    *   `email`: Unique user email.
    *   `family_name`, `first_name`: User's name.
    *   `session_id`: Stores the active session ID for the user.
    *   `is_connected`: Boolean, indicates if the user is currently logged in.
    *   `is_validated`, `is_active`, `is_admin`: Booleans, representing the permission levels.
    *   `last_connection`: Timestamp of the last login.
    *   `country`: User's country, potentially from SSO claims.

*   **`Applications` (applications.py):**
    *   `id`: Primary key.
    *   `name`: Display name of the application.
    *   `code`: Unique code for the application (used in routes and internal logic).
    *   `description`, `icon`: Optional metadata for the application.
    *   `route`: The URL path for the application.
    *   `is_active`: Boolean, enables/disables the application.
    *   `minimum_requirement`: String ("active", "validated", "admin") specifying the minimum user permission level required to *be granted access* to this application.
    *   `created_at`, `updated_at`: Timestamps.

*   **`UserApplicationAccess` (user_app_access.py):**
    *   `id`: Primary key.
    *   `user_id` (Foreign Key to `Users.id`): Links to the user.
    *   `application_id` (Foreign Key to `Applications.id`): Links to the application.
    *   `granted_at`: Timestamp when access was granted.
    *   `granted_by` (Foreign Key to `Users.id`): Optional, indicates which admin granted the access.
    *   `can_read`, `can_write`, `can_delete`: Granular permissions within the application.

**CRUD Operations:** The `haleon/db/crud/` directory contains dedicated functions (`create_user`, `get_application_by_code`, `revoke_user_app_access`, etc.) for interacting with these database models, ensuring consistent and encapsulated data access.

*   **`Logs` (logs.py):**
    *   `id`: Primary key.
    *   `table_name`: Name of the modified table (indexed).
    *   `record_id`: ID of the modified record (indexed).
    *   `operation`: Type of operation ("INSERT", "UPDATE", "DELETE").
    *   `field_name`: Name of the modified field.
    *   `old_value`: Previous value (JSON format, nullable).
    *   `new_value`: New value (JSON format, nullable).
    *   `changed_at`: Timestamp of the change (indexed).
    *   `user_email`: Email of the user who performed the change (indexed, nullable).
    *   `user_permissions`: User permissions at the time of change (JSON format, nullable).
    *   `source`: Source of the modification (e.g., "admin/users", "oob/admin", nullable).
    *   `request_id`: UUID to trace a complete request (indexed, nullable).

### 5.1. Database Audit & Logging System

The application implements a comprehensive hybrid audit logging system that automatically tracks all database changes:

**Architecture:**
*   **SQLite Triggers**: Automatically capture all INSERT, UPDATE, and DELETE operations at the database level.
*   **Application Context Injection**: The `AuditLogger` class injects user context (email, permissions, source, request_id) via a temporary table `_audit_context` that triggers read during execution.

**Components:**
*   **`haleon/db/model/logs.py`**: Defines the `Logs` model with one entry per modified field.
*   **`haleon/db/audit_logger.py`**: Provides the `AuditLogger` class with methods:
    *   `set_context_from_user()`: Sets audit context from a User object.
    *   `with_context()`: Context manager for automatic context management.
    *   `clear_context()`: Cleans up the context after operations.
*   **`haleon/db/triggers.py`**: Dynamically generates SQLite triggers for all tables:
    *   `create_audit_triggers()`: Creates INSERT, UPDATE, and DELETE triggers for a table.
    *   `create_audit_triggers_for_all_tables()`: Creates triggers for all tables automatically.
    *   Triggers read from `_audit_context` to inject user context into logs.
*   **`haleon/db/crud/logs.py`**: Provides functions to query logs:
    *   `get_recent_logs()`: Retrieves the most recent logs.
    *   `get_logs_by_table()`: Retrieves logs for a specific table.
    *   `get_logs_by_user()`: Retrieves logs for a specific user.
    *   `get_logs_by_date_range()`: Retrieves logs within a date range.

**How It Works:**
1. Before any database modification, the application code sets the audit context using `AuditLogger.with_context()` or `AuditLogger.set_context_from_user()`.
2. The context is stored in a temporary SQLite table `_audit_context`.
3. When a database operation occurs (INSERT/UPDATE/DELETE), the SQLite triggers fire automatically.
4. Each trigger reads the context from `_audit_context` and creates log entries in the `Logs` table.
5. For UPDATE operations, only modified fields are logged (comparison between OLD and NEW values).
6. For INSERT operations, all fields are logged with `old_value=NULL`.
7. For DELETE operations, all fields are logged with `new_value=NULL`.
8. After the operation completes, the context is cleared.

**Integration:**
*   All CRUD functions in `haleon/db/crud/` accept optional `audit_user` and `audit_source` parameters.
*   Admin pages automatically pass the current user and source (e.g., "admin/users", "oob/admin") to CRUD functions.
*   The `init_db()` function in `database.py` automatically creates triggers for all tables on startup.
*   The admin overview page (`haleon/pages/admin/overview.py`) displays log statistics including total logs and counts for 24h, 7d, and 30d periods.

## 6. State Management

Reflex's state management is central to the application's reactivity.
*   **`AuthState`**: The global authentication state, containing user details, authentication status, permissions, and accessible applications.
*   **`I18nState`**: (Internationalization State) Provides global translation capabilities, inherited by other states.
*   **`SidebarState`**: Manages the sidebar's open/close status and tracks the `current_app_code_for_menu` to dynamically load admin menu items for the active application.
*   **Inheritance:** States often inherit from `AuthState` or `I18nState` to share common properties and methods, promoting reusability and reducing code.

## 7. UI Components and Pages

*   **`layout` Component:** The highest-level component, providing the consistent application shell (navbar, sidebar, footer) around dynamic page content.
*   **`navbar` Component:** Displays application links based on user permissions and provides user-specific actions (e.g., SSO login, user avatar with session info).
*   **`sidebar` Component:** Offers navigation links, including conditionally displayed administration options and language selectors.
*   **`index.py` & `home.py`:** Landing pages. `index.py` handles the initial view, `home.py` is the default page after login. They now use a shared `welcome_message` component for consistency.
*   **`app_view.py`:** A crucial dynamic page responsible for loading and displaying the content of individual modular applications (e.g., OOB) based on the URL parameter.
*   **Admin Pages (`haleon/pages/admin/`):**
    *   **`users.py`**: Manages user accounts, their active/validated/admin status.
    *   **`applications.py`**: Manages the list of available applications.
    *   **`access.py`**: Manages user-application access grants and revocations.

## 8. Application Modules (`haleon/apps/`)

The `apps/` directory is designed for modularity. Each sub-directory (e.g., `oob/`) contains a distinct application.
*   These applications typically have their own `page.py` (UI), `state.py` (application-specific state), and potentially `api/` and `db/crud/` for their own backend interactions.
*   The `app_view.py` page is responsible for dynamically loading and rendering these application modules.

## 9. Limitations of this Document

This document is based on an interrupted code analysis and `README.md`. Therefore, it provides a strong overview but may not capture every fine-grained detail of all functions, specific API calls within application modules, or very recently introduced code (e.g., some security fixes implemented during this session). A complete manual review of every line of code was not performed.
