"""JSON-only argparse interface for :mod:`local_trader`."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TextIO

from .errors import ArtifactError, GateRejectedError, RegistryError, ValidationError
from .models import GateCriteria, Lifecycle, RiskPolicy
from .registry import StrategyRegistry


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationError(message)


def _add_database_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        dest="command_database",
        help="path to the SQLite registry (may also be supplied before the command)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="local-trader",
        description="Fail-closed local strategy registry and promotion gate",
    )
    parser.add_argument(
        "--db", dest="global_database", help="path to the SQLite registry"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize a registry")
    _add_database_argument(init_parser)
    init_parser.add_argument("--candidate-root", required=True)
    init_parser.add_argument("--promoted-root", required=True)
    init_parser.add_argument("--min-trades", type=int, default=100)
    init_parser.add_argument("--min-profit-factor", type=float, default=1.2)
    init_parser.add_argument("--max-gate-drawdown", type=float, default=15.0)
    init_parser.add_argument("--min-symbols", type=int, default=2)
    init_parser.add_argument("--min-timeframes", type=int, default=2)
    init_parser.add_argument("--max-capital", type=float, default=250.0)
    init_parser.add_argument("--max-position", type=float, default=80.0)
    init_parser.add_argument("--max-exposure", type=float, default=240.0)
    init_parser.add_argument("--max-open-positions", type=int, default=3)
    init_parser.add_argument("--max-daily-loss", type=float, default=10.0)
    init_parser.add_argument("--max-account-drawdown", type=float, default=15.0)

    register_parser = subparsers.add_parser("register", help="register an artifact")
    _add_database_argument(register_parser)
    register_parser.add_argument("--name", "--strategy", dest="name", required=True)
    register_parser.add_argument(
        "--source",
        required=True,
        help=(
            "artifact below candidate/promoted root; promoted copies require an "
            "identical candidate parent"
        ),
    )
    register_parser.add_argument("--description", default="")
    register_parser.add_argument(
        "--parent-version",
        type=int,
        help="required candidate version number for promoted registration",
    )
    register_parser.add_argument(
        "--metadata-json",
        default="{}",
        help=(
            "JSON object stored with the version; promoted registration requires "
            "deployment_manifest"
        ),
    )

    evaluate_parser = subparsers.add_parser("evaluate", help="record an evaluation")
    _add_database_argument(evaluate_parser)
    evaluate_parser.add_argument("--strategy", "--name", dest="strategy", required=True)
    evaluate_parser.add_argument("--version", type=int)
    evaluate_parser.add_argument("--symbol", required=True)
    evaluate_parser.add_argument("--timeframe", required=True)
    evaluate_parser.add_argument("--sample-type", required=True)
    evaluate_parser.add_argument("--net-profit", type=float, required=True)
    evaluate_parser.add_argument("--profit-factor", type=float, required=True)
    evaluate_parser.add_argument("--max-drawdown", type=float, required=True)
    evaluate_parser.add_argument("--win-rate", type=float, required=True)
    evaluate_parser.add_argument("--trade-count", type=int, required=True)
    evaluate_parser.add_argument("--avg-trade", type=float, required=True)
    evaluate_parser.add_argument("--max-daily-loss-abs", type=float, required=True)
    evaluate_parser.add_argument("--trial-id", type=int)
    evaluate_parser.add_argument("--evidence-id")
    evaluate_parser.add_argument("--dataset-sha256")
    evaluate_parser.add_argument(
        "--provenance-json", default="{}", help="JSON object describing data origin"
    )
    evaluate_parser.add_argument("--notes", default="")

    promote_parser = subparsers.add_parser("promote", help="change lifecycle state")
    _add_database_argument(promote_parser)
    promote_parser.add_argument("--strategy", "--name", dest="strategy", required=True)
    promote_parser.add_argument("--version", type=int)
    promote_parser.add_argument(
        "--to",
        dest="to_state",
        required=True,
        choices=[state.value for state in Lifecycle],
    )
    promote_parser.add_argument("--manual-approval", action="store_true")
    promote_parser.add_argument("--approved-by")
    promote_parser.add_argument("--approval-file")
    promote_parser.add_argument("--reason", default="")

    authorize_parser = subparsers.add_parser(
        "authorize", help="verify an exact live artifact for a launcher"
    )
    _add_database_argument(authorize_parser)
    authorize_parser.add_argument("--strategy", "--name", dest="strategy", required=True)
    authorize_parser.add_argument("--version", type=int, required=True)
    authorize_parser.add_argument(
        "--target", required=True, choices=["CANARY", "PRODUCTION"]
    )

    verify_parser = subparsers.add_parser("verify", help="verify immutable artifacts")
    _add_database_argument(verify_parser)
    verify_parser.add_argument("--strategy", "--name", dest="strategy")
    verify_parser.add_argument("--version", type=int)

    list_parser = subparsers.add_parser("list", help="list active strategy versions")
    _add_database_argument(list_parser)
    list_parser.add_argument(
        "--lifecycle", choices=[state.value for state in Lifecycle]
    )

    status_parser = subparsers.add_parser("status", help="show strategy status")
    _add_database_argument(status_parser)
    status_parser.add_argument("--strategy", "--name", dest="strategy", required=True)
    status_parser.add_argument("--version", type=int)

    return parser


def _database(args: argparse.Namespace) -> str:
    database = args.command_database or args.global_database
    if not database:
        raise ValidationError("--db is required")
    return database


def _json_object(raw: str, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label} is invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be a JSON object")
    return value


def _execute(args: argparse.Namespace, *, interactive: bool) -> dict[str, Any]:
    database = _database(args)
    if args.command == "init":
        criteria = GateCriteria(
            min_trade_count=args.min_trades,
            min_profit_factor=args.min_profit_factor,
            max_drawdown_pct=args.max_gate_drawdown,
            min_symbols=args.min_symbols,
            min_timeframes=args.min_timeframes,
            require_positive_holdout=True,
        )
        policy = RiskPolicy(
            max_capital=args.max_capital,
            max_position=args.max_position,
            max_exposure=args.max_exposure,
            max_open_positions=args.max_open_positions,
            max_daily_loss=args.max_daily_loss,
            max_drawdown=args.max_account_drawdown,
        )
        registry = StrategyRegistry.initialize(
            database,
            args.candidate_root,
            args.promoted_root,
            gate_criteria=criteria,
            risk_policy=policy,
        )
        return {"registry": registry.configuration()}

    registry = StrategyRegistry(database)
    if args.command == "register":
        registered = registry.register(
            args.name,
            args.source,
            description=args.description,
            parent_version=args.parent_version,
            metadata=_json_object(args.metadata_json, "--metadata-json"),
        )
        return {"version": registered}
    if args.command == "evaluate":
        evaluation = registry.evaluate(
            args.strategy,
            version=args.version,
            symbol=args.symbol,
            timeframe=args.timeframe,
            sample_type=args.sample_type,
            net_profit=args.net_profit,
            profit_factor=args.profit_factor,
            max_drawdown=args.max_drawdown,
            win_rate=args.win_rate,
            trade_count=args.trade_count,
            avg_trade=args.avg_trade,
            max_daily_loss_abs=args.max_daily_loss_abs,
            trial_id=args.trial_id,
            evidence_id=args.evidence_id,
            dataset_sha256=args.dataset_sha256,
            provenance=_json_object(args.provenance_json, "--provenance-json"),
            notes=args.notes,
        )
        return {"evaluation": evaluation}
    if args.command == "promote":
        target = Lifecycle.coerce(args.to_state)
        if target in {Lifecycle.CANARY, Lifecycle.PRODUCTION}:
            if args.version is None:
                raise ValidationError(
                    "live promotion requires an explicit --version"
                )
            if not interactive:
                raise ValidationError(
                    "CANARY and PRODUCTION promotion require an interactive TTY"
                )
        event = registry.promote(
            args.strategy,
            target,
            version=args.version,
            manual_approval=args.manual_approval,
            approved_by=args.approved_by,
            approval_file=args.approval_file,
            interactive=interactive,
            reason=args.reason,
        )
        return {"promotion": event}
    if args.command == "authorize":
        return {
            "authorization": registry.deployment_authorization(
                args.strategy, args.version, args.target
            )
        }
    if args.command == "verify":
        if args.version is not None and args.strategy is None:
            raise ValidationError("--version requires --strategy")
        if args.strategy:
            try:
                artifact = registry.verify_artifact(
                    args.strategy, version=args.version
                )
            except ArtifactError as exc:
                status = registry.status(args.strategy, version=args.version)
                artifact = dict(status["artifact"])
                artifact.update(
                    {
                        "strategy": status["version"]["strategy"],
                        "version": status["version"]["version"],
                        "error": str(exc),
                        "valid": False,
                    }
                )
            database_integrity = registry.database_integrity()
            return {
                "valid": artifact["valid"] and database_integrity["valid"],
                "artifacts": [artifact],
                "database_integrity": database_integrity,
            }
        artifacts = registry.verify_all()
        database_integrity = registry.database_integrity()
        return {
            "valid": all(item["valid"] for item in artifacts)
            and database_integrity["valid"],
            "artifacts": artifacts,
            "database_integrity": database_integrity,
        }
    if args.command == "list":
        return {"strategies": registry.list_strategies(lifecycle=args.lifecycle)}
    if args.command == "status":
        return {"status": registry.status(args.strategy, version=args.version)}
    raise ValidationError(f"unsupported command: {args.command}")


def _emit(payload: Mapping[str, Any], stream: TextIO) -> None:
    stream.write(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
    stream.flush()


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    stdin: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    try:
        args = build_parser().parse_args(argv)
        input_stream = stdin or sys.stdin
        interactive = bool(
            input_stream.isatty() and output.isatty() and errors.isatty()
        )
        result = _execute(args, interactive=interactive)
        payload: dict[str, Any] = {"ok": True, "command": args.command}
        payload.update(result)
        _emit(payload, output)
        # Verification reports mismatch as structured JSON and a non-zero exit.
        if args.command == "verify" and result.get("valid") is False:
            return 3
        return 0
    except GateRejectedError as exc:
        payload = {
            "ok": False,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "decision": (
                    exc.decision.to_dict()
                    if getattr(exc, "decision", None) is not None
                    else None
                ),
            },
        }
        _emit(payload, errors)
        return 2
    except RegistryError as exc:
        _emit(
            {
                "ok": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            },
            errors,
        )
        return 2
    except (OSError, sqlite3.DatabaseError) as exc:
        _emit(
            {
                "ok": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            },
            errors,
        )
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised through __main__
    raise SystemExit(main())
