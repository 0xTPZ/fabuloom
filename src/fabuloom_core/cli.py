"""Headless command surface for the shared Fabuloom engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .api import serve
from .engine import EngineService
from .paths import FabuloomPaths


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _engine(root: str | None) -> EngineService:
    product_root = Path(__file__).resolve().parents[2]
    return EngineService(FabuloomPaths.discover(product_root=product_root, configured_root=root))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fabuloom", description="Fabuloom Studio shared engine control")
    parser.add_argument("--root", help="Fabuloom runtime root; otherwise FABULOOM_ROOT or local discovery is used")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    projects = commands.add_parser("project")
    project_commands = projects.add_subparsers(dest="project_command", required=True)
    project_commands.add_parser("list")
    create = project_commands.add_parser("create")
    create.add_argument("name")
    create.add_argument("--id")
    show = project_commands.add_parser("show")
    show.add_argument("id")
    update = project_commands.add_parser("update")
    update.add_argument("id")
    update.add_argument("--json-file", required=True)
    update.add_argument("--revision", type=int)
    jobs = commands.add_parser("job")
    job_commands = jobs.add_subparsers(dest="job_command", required=True)
    job_commands.add_parser("list")
    job_create = job_commands.add_parser("create")
    job_create.add_argument("kind", choices=["validate-project", "catalog-scan"])
    job_create.add_argument("--project-id")
    job_create.add_argument("--no-wait", action="store_true", help="return immediately; API/Desktop jobs are asynchronous by default")
    job_show = job_commands.add_parser("show")
    job_show.add_argument("id")
    job_cancel = job_commands.add_parser("cancel")
    job_cancel.add_argument("id")
    api = commands.add_parser("api")
    api.add_argument("--port", type=int, default=8790)
    catalog = commands.add_parser("catalog")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    catalog_commands.add_parser("search").add_argument("query", nargs="?", default="")
    scan = catalog_commands.add_parser("scan")
    scan.add_argument("--root", dest="library_root", required=True)
    scan.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = _engine(args.root if hasattr(args, "root") else None)
    if args.command == "status":
        _json(engine.status())
        return 0
    if args.command == "project":
        if args.project_command == "list":
            _json(engine.list_projects())
        elif args.project_command == "create":
            _json(engine.create_project(args.name, project_id=args.id))
        elif args.project_command == "show":
            _json(engine.get_project(args.id))
        elif args.project_command == "update":
            payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise SystemExit("project JSON must be an object")
            _json(engine.update_project(args.id, payload, expected_revision=args.revision))
        return 0
    if args.command == "job":
        if args.job_command == "list":
            _json(engine.list_jobs())
        elif args.job_command == "create":
            payload = {"project_id": args.project_id} if args.project_id else {}
            created = engine.create_job(args.kind, payload)
            _json(created if args.no_wait else engine.wait_for_job(str(created["id"])))
        elif args.job_command == "show":
            _json(engine.get_job(args.id))
        elif args.job_command == "cancel":
            _json(engine.cancel_job(args.id))
        return 0
    if args.command == "catalog":
        if args.catalog_command == "search":
            _json(engine.search_library(args.query))
        else:
            from .asset_catalog import AssetCatalog

            catalog = AssetCatalog(Path(args.library_root), engine.paths.catalog_db)
            records = catalog.scan(dry_run=args.dry_run)
            _json({"records": len(records), "dry_run": args.dry_run})
        return 0
    if args.command == "api":
        serve(engine, port=args.port)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
