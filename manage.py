#!/usr/bin/env python
"""Django-style management CLI for the FastAPI template."""

import asyncio
import getpass
import re
import subprocess
import sys
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parent
app = typer.Typer(help="FastAPI template management commands.")

# Directories that should not trigger uvicorn --reload (e.g. pip installs in venv).
RELOAD_EXCLUDE_DIRS = ("venv", "media", "__pycache__", ".git")


def _alembic_config() -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    return cfg


@app.command()
def runserver(
    host: str = typer.Option(None, help="Bind host"),
    port: int = typer.Option(None, help="Bind port"),
    reload: bool = typer.Option(True, help="Auto-reload on code changes"),
):
    """Start the development server (like django runserver)."""
    from core.settings import settings

    bind_host = host or settings.HOST
    bind_port = port or settings.PORT

    typer.echo(f"Starting server at http://{bind_host}:{bind_port}")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        bind_host,
        "--port",
        str(bind_port),
    ]
    if reload:
        cmd.append("--reload")
        for exclude_dir in RELOAD_EXCLUDE_DIRS:
            cmd.extend(["--reload-exclude", exclude_dir])

    subprocess.run(cmd, cwd=str(ROOT))


@app.command("migrate")
def migrate(
    revision: str = typer.Option("head", "--revision", "-r", help="Target revision"),
):
    """Apply database migrations (alembic upgrade)."""
    typer.echo(f"Applying migrations to {revision}...")
    command.upgrade(_alembic_config(), revision)
    typer.echo("Done.")


@app.command("makemigrations")
def makemigrations(
    message: str = typer.Option(..., "-m", "--message", help="Migration description"),
):
    """Auto-generate a migration from model changes."""
    typer.echo("Generating migration...")
    command.revision(_alembic_config(), message=message, autogenerate=True)
    typer.echo("Done. Review the file in alembic/versions/ before migrating.")


@app.command("createsuperuser")
def createsuperuser():
    """Create an admin superuser account."""
    asyncio.run(_createsuperuser())


async def _createsuperuser():
    from sqlalchemy.ext.asyncio import AsyncSession

    from core.security import hash_password
    from database.db import async_session_factory
    from modules.user.repository import UserRepository

    email = typer.prompt("Email")
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Password (again): ")

    if password != password_confirm:
        typer.echo("Error: passwords do not match.", err=True)
        raise typer.Exit(1)

    full_name = typer.prompt("Full name", default="")

    async with async_session_factory() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(email)
        if existing:
            typer.echo(f"Error: user with email {email} already exists.", err=True)
            raise typer.Exit(1)

        user = await repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name or None,
            is_superuser=True,
        )
        await session.commit()
        typer.echo(f"Superuser created: {user.email} (id={user.id})")


@app.command()
def shell():
    """Open an interactive Python shell with app context."""
    typer.echo("Starting shell — app modules are pre-imported.")
    banner = "FastAPI Template Shell"
    namespace = {
        "settings": __import__("core.settings", fromlist=["settings"]).settings,
        "User": __import__("database.models.user", fromlist=["User"]).User,
    }
    try:
        from IPython import embed

        embed(banner1=banner, user_ns=namespace)
    except ImportError:
        import code

        code.interact(banner=banner, local=namespace)


@app.command("runworker")
def runworker(
    backend: str = typer.Option(
        None,
        "--backend",
        "-b",
        help="Task backend: apscheduler, celery, or arq",
    ),
    beat: bool = typer.Option(False, help="Run Celery Beat scheduler (celery only)"),
):
    """Run background task worker."""
    from core.settings import settings

    chosen = backend or settings.TASK_BACKEND

    if beat:
        if chosen != "celery":
            typer.echo("Error: --beat is only supported with celery backend.", err=True)
            raise typer.Exit(1)
        typer.echo("Starting Celery Beat...")
        subprocess.run(
            [sys.executable, "-m", "celery", "-A", "tasks.celery_app.celery_app", "beat", "--loglevel=info"],
            cwd=str(ROOT),
        )
        return

    typer.echo(f"Starting {chosen} worker...")
    if chosen == "apscheduler":
        from tasks.scheduler import run_forever

        run_forever()
    elif chosen == "celery":
        subprocess.run(
            [sys.executable, "-m", "celery", "-A", "tasks.celery_app.celery_app", "worker", "--loglevel=info"],
            cwd=str(ROOT),
        )
    elif chosen == "arq":
        subprocess.run(
            [sys.executable, "-m", "arq", "tasks.arq_worker.WorkerSettings"],
            cwd=str(ROOT),
        )
    else:
        typer.echo(f"Error: unknown backend '{chosen}'. Use apscheduler, celery, or arq.", err=True)
        raise typer.Exit(1)


@app.command("seed-data")
def seed():
    """Seed roles, permissions, and default data."""
    asyncio.run(_seed())


async def _seed():
    from database.db import async_session_factory
    from database.seed import seed as run_seed

    async with async_session_factory() as session:
        await run_seed(session)
    typer.echo("Seed data applied.")


@app.command("collectstatic")
def collectstatic():
    """Collect static files to COLLECTSTATIC_ROOT or S3."""
    import shutil

    from core.settings import settings

    dest = settings.COLLECTSTATIC_ROOT
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(settings.STATIC_ROOT, dest)
    typer.echo(f"Static files collected to {dest}")

    if settings.STORAGE_BACKEND == "s3":
        typer.echo("Upload collected static files to S3 manually or extend this command.")


@app.command("backup-db")
def backupdb():
    """Backup the database."""
    asyncio.run(_backupdb())


async def _backupdb():
    from database.db import async_session_factory
    from database.backup import backup as run_backup

    async with async_session_factory() as session:
        await run_backup(session)

    typer.echo("Database backup completed.")


@app.command("restore-db")
def restoredb(
    backup_file: str = typer.Argument(..., help="Backup filename or path"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Restore the database from a backup file."""
    if not yes:
        typer.confirm(
            "This will overwrite the current database. Continue?",
            abort=True,
        )
    asyncio.run(_restoredb(backup_file))


async def _restoredb(backup_file: str):
    from database.backup import restore as run_restore

    await run_restore(backup_file)
    typer.echo(f"Database restored from {backup_file}.")


@app.command("create-module")
def createmodule(
    name: str = typer.Argument(..., help="Name of the new module (snake_case)"),
):
    """Scaffold a new module under modules/."""
    _createmodule(name)


def _class_name(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))


def _createmodule(name: str) -> None:
    """
    Create modules/{name}/ with:
        __init__.py, router.py, service.py, schemas.py, repository.py, template/
    """
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        typer.echo(
            f"Error: Module name '{name}' must be snake_case (e.g. blog_post).",
            err=True,
        )
        raise typer.Exit(1)

    module_dir = ROOT / "modules" / name
    if module_dir.exists():
        typer.echo(f"Error: Module '{name}' already exists at {module_dir}.", err=True)
        raise typer.Exit(1)

    class_name = _class_name(name)
    (module_dir / "template").mkdir(parents=True)

    files_content = {
        "__init__.py": f"# {name} module\n",
        "router.py": (
            f'"""Routes for the {name} module."""\n\n'
            f"from fastapi import APIRouter\n\n"
            f'router = APIRouter(prefix="/{name}", tags=["{name}"])\n'
        ),
        "service.py": (
            f'"""Business logic for the {name} module."""\n\n'
            f"from sqlalchemy.ext.asyncio import AsyncSession\n\n"
            f"from modules.{name}.repository import {class_name}Repository\n\n\n"
            f"class {class_name}Service:\n"
            f"    def __init__(self, db: AsyncSession):\n"
            f"        self.db = db\n"
            f"        self.repo = {class_name}Repository(db)\n"
        ),
        "schemas.py": (
            f'"""Pydantic schemas for the {name} module."""\n\n'
            f"from pydantic import BaseModel\n"
        ),
        "repository.py": (
            f'"""Data access for the {name} module."""\n\n'
            f"from sqlalchemy.ext.asyncio import AsyncSession\n\n\n"
            f"class {class_name}Repository:\n"
            f"    def __init__(self, db: AsyncSession):\n"
            f"        self.db = db\n"
        ),
    }

    for fname, content in files_content.items():
        (module_dir / fname).write_text(content, encoding="utf-8")

    typer.echo(f"Module '{name}' created at {module_dir.relative_to(ROOT)}")
    typer.echo(f"Next: create database/models/{name}.py, then run:")
    typer.echo(f"  python manage.py generate-crud {name}")


@app.command("generate-crud")
def generatecrud(
    name: str = typer.Argument(..., help="Module name (snake_case), e.g. blog"),
    filters: bool = typer.Option(False, "--filters", help="Generate filters.py and list filtering"),
    permissions: bool = typer.Option(False, "--permissions", help="Generate permissions.py and protect routes"),
    tests: bool = typer.Option(False, "--tests", help="Generate CRUD tests in tests/"),
):
    """Generate CRUD code from a SQLAlchemy model in database/models/."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        typer.echo(
            f"Error: Module name '{name}' must be snake_case (e.g. blog_post).",
            err=True,
        )
        raise typer.Exit(1)

    from generators.crud import generate_crud

    try:
        written = generate_crud(
            name,
            with_filters=filters,
            with_permissions=permissions,
            with_tests=tests,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Generated CRUD for '{name}':")
    seen: set[str] = set()
    for path in written:
        if path not in seen:
            typer.echo(f"  [ok] {path}")
            seen.add(path)

    if permissions:
        typer.echo("  [note] Run: python manage.py seed-data")
    typer.echo(f'  [note] Review and run: python manage.py makemigrations -m "add {name}"')
    typer.echo("  [ok] Router auto-discovered on next server start")


if __name__ == "__main__":
    app()
