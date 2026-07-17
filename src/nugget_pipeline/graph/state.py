from typing import TypedDict, List, Dict, Any


class DataCollectionState(TypedDict, total=False):
    # raw QA branch
    enable_raw_qa: bool

    # category/topic selection input
    categories: List[Dict[str, Any]]

    # new topic selector controls
    articles_per_focus: int
    extra_articles_per_category: int

    # topic selector output
    topics_by_category: Dict[str, List[dict]]
    topics: List[str]

    # fetch from url
    article_urls: List[str]

    # pre-fetched document discovery
    raw_documents_dir: str
    news_articles_dir: str
    output_filename_stems: Dict[str, str]
    article_titles: Dict[str, str]
    source_document_paths: Dict[str, List[str]]

    # wikipedia + chunking
    raw_article_paths: List[str]
    article_chunks: Dict[str, List[str]]

    # outputs
    nugget_output_dir: str
    nugget_qa_output_dir: str
    nugget_manifest_path: str
    raw_qa_paths: List[str]
    nugget_paths: List[str]
    nugget_qa_paths: List[str]

    # nugget policy
    retain_source_details: bool
    retain_all_supported_nuggets: bool

    # testing limits
    max_categories: int
    max_articles: int
    max_entities: int
    max_documents_per_entity: int
    max_chunks_per_article: int
    max_nuggets_per_chunk: int
    max_nuggets_per_article: int

    # logs
    errors: List[str]


