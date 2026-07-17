import json

from src.nugget_pipeline.config import OUTPUT_DIR
from src.nugget_pipeline.raw_qa_generator import generate_raw_qa_from_chunk


RAW_QA_DIR = OUTPUT_DIR / "raw_qa"
RAW_QA_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(title: str) -> str:
    return title.replace(" ", "_").replace("/", "_")


def raw_qa_node(state):
    print("Starting raw QA generation...")

    output_paths = []

    for title, chunks in state["article_chunks"].items():
        print(f"Starting raw QA generation for: {title}")

        output_path = RAW_QA_DIR / f"{safe_filename(title)}.jsonl"

        if output_path.exists():
            output_paths.append(str(output_path))
            print(f"Finished raw QA generation for: {title} (cached)")
            continue

        all_qa = []

        for chunk_index, chunk in enumerate(chunks, start=1):
            print(f"Starting raw QA chunk {chunk_index}/{len(chunks)} for: {title}")
            qa_pairs = generate_raw_qa_from_chunk(
                article_title=title,
                chunk=chunk,
                questions_per_chunk=3,
            )
            all_qa.extend(qa_pairs)
            print(
                f"Finished raw QA chunk {chunk_index}/{len(chunks)} "
                f"for: {title}. Generated {len(qa_pairs)} QA pairs."
            )

        with output_path.open("w", encoding="utf-8") as f:
            for qa in all_qa:
                f.write(json.dumps(qa, ensure_ascii=False) + "\n")

        output_paths.append(str(output_path))
        print(
            f"Finished raw QA generation for: {title}. "
            f"Generated {len(all_qa)} QA pairs."
        )

    print(f"Finished raw QA generation. Created {len(output_paths)} files.")

    return {"raw_qa_paths": output_paths}

