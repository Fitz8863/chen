# AGENTS.md - Code Guidelines for This Project

## 全局规则 (Global Rules)

**必须始终使用中文回答所有问题。** (Always answer all questions in Chinese.)

## 1. Project Overview

- **Project Name**: 校园安防智能监测系统 (Campus Security Intelligent Monitoring System)
- **Framework**: Flask 3.1+ with Blueprint architecture
- **Database**: MySQL (host: 127.0.0.1, port: 3306, user: root, password: heweijie, db: `home`) via SQLAlchemy 2.0
- **Frontend**: HTML + Bootstrap 5 + JavaScript (Jinja2 templates)
- **Real-time**: Flask-SocketIO for live updates
- **AI Inference**: YOLO (ONNX) + VLM (Qwen via DashScope API) for behavior analysis
- **Python Version**: 3.10+
- **Environment**: Conda env named `bishe` (includes ROS2 packages)

## 2. Build / Run Commands

### Start the Application
```bash
# Ensure you are in the project root
conda activate bishe
python app.py
```
App runs on `http://0.0.0.0:5000` with SocketIO support. Debug mode is disabled in production.

### Database Setup
Tables are auto-created on app startup via `db.create_all()` in `blueprints/__init__.py`.
To initialize manually:
```bash
mysql -u root -pheweijie -e "CREATE DATABASE IF NOT EXISTS home DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
```
**Note**: No migration tool (Alembic/Flask-Migrate) is used. Schema changes require manual DB updates or dropping tables.

### Testing
No test suite currently exists. If adding tests:
```bash
# Run all tests
pytest tests/

# Run a single test case
pytest tests/test_auth.py::test_login -v
```

### Linting
If adding linting tools:
```bash
# Run Black for formatting
black .

# Run Flake8 for linting
flake8 . --max-line-length=120
```

## 3. Code Style Guidelines

### 3.1 Structure
- `app.py`: Entry point, registers blueprints, initializes extensions, starts video inference daemon.
- `config.py`: Configuration (DB, mail, YOLO, VLM). **Hardcoded credentials — do not commit changes.**
- `exts.py`: Flask extension instances (db, socketio, mail) to avoid circular imports.
- `blueprints/`: Modular logic (MVC controllers).
- `templates/`: Jinja2 templates inheriting from `base.html`.
- `static/`: CSS, JS, uploaded captures.
- `model/`: YOLO ONNX model files.

### 3.2 Import Order
1. Standard library (`os`, `json`, `datetime`)
2. Third-party (`flask`, `sqlalchemy`, `flask_socketio`)
3. Local application imports (`.models`, `exts`, `config`)

### 3.3 Naming Conventions
- **Files/Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Blueprints**: `snake_case` with `_bp` suffix (e.g., `auth_bp`)

### 3.4 Blueprint Structure & API Design
- Use `url_prefix` in Blueprint definitions.
- API Endpoints: `/api/` prefix, return `jsonify()`.
- UI routes: return `render_template()`.

### 3.5 Error Handling
- **Database**: `try-except`, `db.session.rollback()` on failure.
- **API**: JSON response with `error` key, proper HTTP status codes.
- **UI**: Use `flash(message, category)`.

### 3.6 Role-Based Access Control (RBAC)
- Roles: `admin`, `assistant`, `user`.
- Use `@admin_required` or `@super_admin_required` from `blueprints.auth`.

## 4. Agentic Development Workflow

- **Think Before Act**: For complex tasks, create a plan and `todowrite` checklist first.
- **Verify Before Commit**: Always run `flake8` and test affected endpoints.
- **Minimalist Fixes**: Only fix what is broken. Do not refactor unrelated code.
- **Database Migrations**: Manually check `blueprints/models.py` against MySQL table structure (`DESCRIBE table_name;`) before altering schema.
- **Code Reviews**: When an agent proposes significant changes, verify them using `flake8` and local manual testing before finalizing the commit.

## 5. Git Workflow & PR Policy
- **Branching**: Use `feature/` for new capabilities, `fix/` for bug repairs, and `refactor/` for structural improvements.
- **Commits**: Follow conventional commits: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- **Pull Requests**:
    - Include a clear description of the problem solved.
    - Reference specific issue numbers if applicable.
    - Attach screenshots for UI-related changes.
    - Run the full test suite (`pytest`) before marking a PR as ready for review.

## 6. Advanced Troubleshooting
- **SQLAlchemy Debugging**: Enable `SQLALCHEMY_ECHO = True` in `config.py` to see generated SQL queries for debugging model interactions.
- **Live Updates**: Debug SocketIO using the browser console to track `disconnect` and `connect` events, and use the server logs to monitor for `SocketIO` errors or connection drops.
- **Memory/Process Management**: If the video inference daemon hangs, use `ps -ef | grep video_inference.py` to identify and terminate orphaned processes before restarting the system.
- **Environment Issues**: If Conda environments fail, ensure `requirements.txt` is updated after installing new packages and run `conda clean -a` to free up disk space.

## 7. Frontend & UI
- **Bootstrap 5**: Prefer utility classes (e.g., `d-flex`, `p-3`) over adding custom CSS whenever possible to maintain consistency with the default Bootstrap theme.
- **Jinja2**: Keep templates DRY by using `{% extends 'base.html' %}` and `{% block content %}` for all new UI pages.
- **JavaScript**: Use `fetch` API for all asynchronous communication with `/api/` endpoints. Keep JS code in separate files in `static/js/` wherever possible, rather than inline `<script>` blocks.
- **Accessibility**: Ensure basic accessibility compliance (e.g., proper contrast for text, alt text for images) in all new UI components.

## 8. Agent Instructions & AI/Inference
- **Circular Imports**: Always use `exts.py` for shared extensions. Never import `app` directly into blueprints.
- **AI Inference**: `video_inference.py` runs as singleton daemon on startup. Guard with `WERKZEUG_RUN_MAIN` check to prevent multiple instances during development.
- **ROS2**: Do not remove from `requirements.txt`.
- **Cameras Configuration**: `cameras.json` handles static camera mappings. Any change to camera connectivity requires updating this file and potentially restarting the inference daemon.
- **Captures Directory**: `static/captures/` stores all uploaded alert images. Agents should periodically check if image storage space needs cleanup, as this directory can grow indefinitely with thousands of alert images.

## 9. Deployment Considerations
- **Environment Variables**: Sensitive credentials in `config.py` should be moved to environment variables for production environments to avoid hardcoding secrets in version control.
- **Production Server**: The Flask development server is not suitable for production. Use a proper WSGI server like `gunicorn` with `eventlet` or `gevent` support for SocketIO compatibility.

## 10. Security Best Practices
- **Input Sanitization**: Always sanitize input from API endpoints and form submissions to prevent SQL injection and XSS. SQLAlchemy handles parameterization, so avoid `execute()` calls with raw SQL strings.
- **Authentication**: Ensure all routes that require authentication use the `@login_required` decorator from `flask_login`.
- **Dependency Auditing**: Regularly run `pip-audit` to identify and fix known vulnerabilities in project dependencies.

## 11. Performance Optimization
- **Database Indexing**: For tables with high frequent queries (e.g., `Capture` logs), ensure database indexes are correctly defined on frequently filtered columns (like `camera_id` or `timestamp`).
- **Static Assets**: Use cache headers for static files (`static/`) to improve page load times for end users.
- **Asset Minification**: Consider using a pipeline (like `Flask-Assets`) to minify JS and CSS files for production.

