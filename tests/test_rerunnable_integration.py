import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.fetcher.schemas import Document
from src.fetcher import node as fetcher_node_module
from src.fetcher import saver as fetcher_saver
from src.schemas.entity import Entity
from src.search.schemas import SearchPlan, SearchResult, SearchTask
from src.nugget_pipeline.nodes import nugget_qa_node as nugget_module


class DiscoveryFetchManifestTests(unittest.TestCase):
    def test_fetcher_reuses_manifest_document_without_refetching(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            raw_dir = data_dir / "raw_documents"
            manifest_path = data_dir / "manifests" / "discovery_manifest.json"

            entity = Entity(
                title="Entity",
                url="https://example.test/entity",
                depth=0,
            )
            entity.search_plan = SearchPlan(
                tasks=[
                    SearchTask(
                        information="overview",
                        query="entity overview",
                        results=[
                            SearchResult(
                                url="https://example.test/source-a",
                                title="Source A",
                                reason="test",
                            )
                        ],
                    )
                ]
            )
            document = Document(
                url="https://example.test/source-a",
                source="example.test",
                title="Source A",
                text="Cached fact.",
            )

            with (
                patch.object(fetcher_saver, "OUTPUT_DIR", raw_dir),
                patch.object(fetcher_node_module, "DATA_DIR", data_dir),
                patch.object(
                    fetcher_node_module,
                    "DISCOVERY_MANIFEST_PATH",
                    manifest_path,
                ),
            ):
                path = fetcher_saver.save_document(entity, document)
                manifest = fetcher_node_module.empty_discovery_manifest()
                fetcher_node_module.record_fetched_document(
                    manifest,
                    entity,
                    document,
                    path,
                )
                fetcher_node_module.save_discovery_manifest(manifest)

                with patch.object(fetcher_node_module, "FetcherClient") as client_cls:
                    client_cls.return_value.fetch.side_effect = AssertionError(
                        "network fetch should not be called"
                    )
                    result = fetcher_node_module.fetcher_node(
                        {"discovered_entities": [entity]}
                    )

            documents = result["discovered_entities"][0].documents
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].url, "https://example.test/source-a")

    def test_save_document_uses_url_hash_to_avoid_same_domain_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_dir = Path(temporary_directory)
            entity = Entity(
                title="Entity",
                url="https://example.test/entity",
                depth=0,
            )
            first = Document(
                url="https://example.test/a",
                source="example.test",
                title="A",
                text="First.",
            )
            second = Document(
                url="https://example.test/b",
                source="example.test",
                title="B",
                text="Second.",
            )

            with patch.object(fetcher_saver, "OUTPUT_DIR", raw_dir):
                first_path = fetcher_saver.save_document(entity, first)
                second_path = fetcher_saver.save_document(entity, second)

            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.exists())
            self.assertTrue(second_path.exists())
            self.assertEqual(
                json.loads(first_path.read_text(encoding="utf-8"))["url"],
                "https://example.test/a",
            )


class QaManifestResumeTests(unittest.TestCase):
    def test_existing_nuggets_are_reused_when_qa_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nugget_dir = root / "output" / "nugget_discovery"
            qa_dir = root / "output" / "nugget_qa_discovery"
            manifest_path = root / "manifests" / "nugget_manifest.json"
            nugget_dir.mkdir(parents=True)
            qa_dir.mkdir(parents=True)

            existing_nuggets = [
                {
                    "nugget_id": "ng_existing",
                    "text": "Kaynak mevcut bir bilgi verir.",
                    "importance": 8,
                    "source_article": "Entity Name",
                    "detail_level": "high",
                    "questions_per_nugget": 1,
                    "storage_action": "keep_full",
                    "storage_reason": "test",
                }
            ]
            nugget_path = nugget_dir / "Entity Name.json"
            nugget_path.write_text(
                json.dumps(existing_nuggets, ensure_ascii=False),
                encoding="utf-8",
            )

            qa_pair = {
                "nugget_id": "ng_existing",
                "question": "Kaynak ne verir?",
                "answer": "Bir bilgi.",
                "source_article": "Entity Name",
                "storage_type": "nugget_qa",
            }

            with (
                patch.object(
                    nugget_module,
                    "update_nuggets_with_chunk",
                    side_effect=AssertionError("should reuse existing nuggets"),
                ),
                patch.object(
                    nugget_module,
                    "validate_nuggets_against_chunk",
                    side_effect=AssertionError("should reuse existing nuggets"),
                ),
                patch.object(
                    nugget_module,
                    "generate_qa_from_nuggets",
                    return_value=[qa_pair],
                ),
            ):
                result = nugget_module.nugget_qa_node(
                    {
                        "article_chunks": {"Entity Name": ["Source chunk"]},
                        "output_filename_stems": {"Entity Name": "Entity Name"},
                        "source_document_paths": {
                            "Entity Name": [str(root / "raw_documents" / "doc.json")]
                        },
                        "nugget_output_dir": str(nugget_dir),
                        "nugget_qa_output_dir": str(qa_dir),
                        "nugget_manifest_path": str(manifest_path),
                    }
                )

            qa_path = qa_dir / "Entity Name.jsonl"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(result["nugget_paths"], [str(nugget_path)])
            self.assertEqual(result["nugget_qa_paths"], [str(qa_path)])
            self.assertEqual(
                json.loads(nugget_path.read_text(encoding="utf-8")),
                existing_nuggets,
            )
            self.assertEqual(
                json.loads(qa_path.read_text(encoding="utf-8")),
                qa_pair,
            )
            self.assertEqual(
                manifest["entities"]["Entity Name"]["nugget_ids"],
                ["ng_existing"],
            )
            self.assertEqual(
                manifest["entities"]["Entity Name"]["status"],
                "completed",
            )


if __name__ == "__main__":
    unittest.main()

