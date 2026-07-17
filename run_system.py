import argparse
import os
import sys
from pathlib import Path


DEFAULT_SEEDS = {
    "T\u00fcrk mutfa\u011f\u0131": 2,
    "T\u00fcrk k\u00fclt\u00fcr\u00fc": 4,
    "T\u00fcrkiye'de turizm": 2,
    "T\u00fcrk folkloru": 2,
    "T\u00fcrkiye'de e\u011fitim": 1,
    "T\u00fcrkiye'de spor": 2,
    "T\u00fcrk m\u00fczi\u011fi": 2,
    "T\u00fcrk edebiyat\u0131": 2,
    "T\u00fcrkiye'de mimarl\u0131k": 1,
    "T\u00fcrkiye'nin illeri": 2,
}


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def configure_data_dir(data_dir: Path) -> Path:
    resolved = data_dir.expanduser().resolve()
    os.environ["PIPELINE_DATA_DIR"] = str(resolved)
    return resolved


def parse_seed_specs(seed_specs: list[str] | None) -> dict[str, int]:
    if not seed_specs:
        return dict(DEFAULT_SEEDS)

    seeds = {}

    for spec in seed_specs:
        if ":" not in spec:
            raise ValueError(
                f"Seed must use TITLE:DEPTH format, got: {spec}"
            )

        title, depth = spec.rsplit(":", 1)
        title = title.strip()

        if not title:
            raise ValueError(f"Seed title is empty in: {spec}")

        seeds[title] = int(depth)

    return seeds


def run_discovery(args) -> None:
    from src.graph.workflow import build_graph
    from src.schemas.seed import Seed

    seeds = parse_seed_specs(args.seed)
    app = build_graph()

    for title, depth in seeds.items():
        print(
            f"Running discovery for: {title} "
            f"(depth={depth})"
        )

        result = app.invoke(
            {
                "seed": Seed(
                    title=title,
                    max_depth=depth,
                    entity_limit=args.entity_limit,
                ),
                "refresh_discovery": args.refresh or args.refresh_discovery,
                "refresh_enrichment": args.refresh or args.refresh_enrichment,
                "refresh_planner": args.refresh or args.refresh_planner,
                "refresh_search": args.refresh or args.refresh_search,
                "refresh_fetch": args.refresh or args.refresh_fetch,
            }
        )

        print(
            "Discovery finished for "
            f"{title} with "
            f"{len(result.get('discovered_entities', []))} "
            "planned entities."
        )


def run_nugget_pipeline(args, data_dir: Path) -> None:
    from src.nugget_pipeline.graph_documents.workflow import (
        build_graph as build_raw_documents_graph,
    )

    raw_documents_dir = args.raw_documents_dir or data_dir / "raw_documents"
    nugget_output_dir = (
        args.nugget_output_dir
        or data_dir / "output" / "nugget_discovery"
    )
    nugget_qa_output_dir = (
        args.nugget_qa_output_dir
        or data_dir / "output" / "nugget_qa_discovery"
    )
    nugget_manifest_path = (
        args.nugget_manifest_path
        or data_dir / "manifests" / "nugget_manifest.json"
    )

    app = build_raw_documents_graph()

    print(f"Starting nugget pipeline from: {raw_documents_dir}")
    print(f"Writing nuggets to: {nugget_output_dir}")
    print(f"Writing nugget QA to: {nugget_qa_output_dir}")
    print(f"Writing nugget manifest to: {nugget_manifest_path}")

    result = app.invoke(
        {
            "raw_documents_dir": str(raw_documents_dir),
            "nugget_output_dir": str(nugget_output_dir),
            "nugget_qa_output_dir": str(nugget_qa_output_dir),
            "nugget_manifest_path": str(nugget_manifest_path),
            "max_entities": args.max_entities,
            "max_documents_per_entity": args.max_documents_per_entity,
            "max_chunks_per_article": args.max_chunks_per_entity,
            "max_nuggets_per_chunk": args.max_nuggets_per_chunk,
            "max_nuggets_per_article": args.max_nuggets_per_entity,
            "retain_source_details": True,
            "retain_all_supported_nuggets": True,
            "errors": [],
        }
    )

    print(f"Nugget files: {len(result.get('nugget_paths', []))}")
    print(f"Nugget QA files: {len(result.get('nugget_qa_paths', []))}")
    print("Errors:", result.get("errors", []))
    print("Nugget pipeline finished.")


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Single root directory for raw documents, output, caches, and manifests.",
    )


def add_discovery_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--seed",
        action="append",
        help="Seed in TITLE:DEPTH format. Can be provided multiple times.",
    )
    parser.add_argument(
        "--entity-limit",
        type=int,
        default=250,
        help="Maximum entities discovered per seed.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Recompute every discovery stage and refetch documents.",
    )
    parser.add_argument("--refresh-discovery", action="store_true")
    parser.add_argument("--refresh-enrichment", action="store_true")
    parser.add_argument("--refresh-planner", action="store_true")
    parser.add_argument("--refresh-search", action="store_true")
    parser.add_argument("--refresh-fetch", action="store_true")


def add_nugget_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--raw-documents-dir", type=Path)
    parser.add_argument("--nugget-output-dir", type=Path)
    parser.add_argument("--nugget-qa-output-dir", type=Path)
    parser.add_argument(
        "--nugget-manifest-path",
        "--qa-manifest-path",
        dest="nugget_manifest_path",
        type=Path,
    )
    parser.add_argument("--max-entities", type=int)
    parser.add_argument("--max-documents-per-entity", type=int)
    parser.add_argument("--max-chunks-per-entity", type=int)
    parser.add_argument(
        "--max-nuggets-per-chunk",
        type=int,
        default=80,
    )
    parser.add_argument(
        "--max-nuggets-per-entity",
        type=int,
        default=2000,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the merged discovery and nugget pipelines."
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    discover = subparsers.add_parser("discover")
    add_common_arguments(discover)
    add_discovery_arguments(discover)

    nugget = subparsers.add_parser(
        "nugget",
        aliases=["qa"],
    )
    add_common_arguments(nugget)
    add_nugget_arguments(nugget)

    all_parser = subparsers.add_parser("all")
    add_common_arguments(all_parser)
    add_discovery_arguments(all_parser)
    add_nugget_arguments(all_parser)

    return parser


def main() -> None:
    configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args()
    data_dir = configure_data_dir(args.data_dir)

    if args.command == "discover":
        run_discovery(args)
    elif args.command in {"nugget", "qa"}:
        run_nugget_pipeline(args, data_dir)
    elif args.command == "all":
        run_discovery(args)
        run_nugget_pipeline(args, data_dir)
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()

