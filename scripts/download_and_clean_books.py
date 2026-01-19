import json
import time
from csv import DictReader, DictWriter
from pathlib import Path

from loguru import logger
from tap import Tap
from tqdm import tqdm

from literaryqa.clean import clean_and_save, detect_encoding_and_read, extract_raw_text
from literaryqa.download import download_htm_from_gutenberg


ANNOTATIONS_FOLDER = Path("data/annotations")
LITERARYQA_URLS = Path("data/literaryqa_urls.tsv")

MAX_DOWNLOAD_RETRIES = 3
RETRY_SLEEP_SECONDS = 2


class ScriptArgs(Tap):
    """Command-line arguments for the downloader script."""
    output_dir: Path = Path("data/literaryqa")
    write_as_jsonl: bool = False

    def process_args(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logging_dir = self.output_dir / "logs"
        self.logging_dir.mkdir(parents=True, exist_ok=True)


def download_with_retry(
    book_id: str,
    split: str,
    url: str,
    output_dir: Path,
    logging_dir: Path,
    pbar,
):
    """Download a Gutenberg HTML file with retries and logging."""
    html_path = output_dir / split / f"{book_id}.htm"
    html_path.parent.mkdir(parents=True, exist_ok=True)

    if html_path.exists():
        logger.info(f"[SKIP DOWNLOAD] {book_id} already exists")
        return html_path

    for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
        logger.info(f"[DOWNLOAD] {book_id} attempt {attempt}/{MAX_DOWNLOAD_RETRIES}")
        result = download_htm_from_gutenberg(
            book_id=book_id,
            split=split,
            save_dir=output_dir,
            log_dir=logging_dir,
            pbar=pbar,
        )

        if result is not None and html_path.exists():
            return html_path

        if attempt < MAX_DOWNLOAD_RETRIES:
            logger.warning(
                f"[RETRY] Download failed for {book_id}, retrying..."
            )
            time.sleep(RETRY_SLEEP_SECONDS)

    logger.error(f"[FAILED] Download permanently failed for {book_id}")
    return None


def main(args: ScriptArgs) -> None:
    logger.info(f"Starting process. Output dir: {args.output_dir}")

    # Load URLs
    literaryqa_urls = {}
    with LITERARYQA_URLS.open("r", encoding="utf-8") as f:
        reader = DictReader(f, delimiter="\t")
        for row in reader:
            split = row["split"]
            literaryqa_urls.setdefault(split, []).append(
                (row["id"], row["book_id"], row["url"])
            )

    logger.info(
        "Split counts: "
        + str({k: len(v) for k, v in literaryqa_urls.items()})
    )

    # -------------------
    # DOWNLOAD STEP
    # -------------------
    errors = []

    for split, samples in literaryqa_urls.items():
        logger.info(f"Downloading split: {split}")
        for doc_id, book_id, url in (pbar := tqdm(samples, desc=f"Downloading {split}")):
            result = download_with_retry(
                book_id=book_id,
                split=split,
                url=url,
                output_dir=args.output_dir,
                logging_dir=args.logging_dir,
                pbar=pbar,
            )
            if result is None:
                errors.append(
                    {"doc_id": doc_id, "book_id": book_id, "split": split, "url": url}
                )

    if errors:
        error_log = args.logging_dir / "failed_literaryqa_downloads.tsv"
        with error_log.open("w", encoding="utf-8") as f:
            writer = DictWriter(
                f,
                fieldnames=["doc_id", "book_id", "split", "url"],
                delimiter="\t",
            )
            writer.writeheader()
            for err in errors:
                writer.writerow(err)
        logger.error(f"Logged {len(errors)} download failures to {error_log}")

    # -------------------
    # CLEANING STEP
    # -------------------
    for split, samples in literaryqa_urls.items():
        logger.info(f"Cleaning split: {split}")
        processed = 0
        missing = []

        (args.logging_dir / split).mkdir(parents=True, exist_ok=True)

        for _, book_id, _ in (pbar := tqdm(samples, desc=f"Cleaning {split}")):
            input_html = args.output_dir / split / f"{book_id}.htm"
            output_txt = args.output_dir / split / f"{book_id}.cleaned.txt"
            log_file = args.logging_dir / split / f"{book_id}_cleaning.log"

            if output_txt.exists():
                logger.info(f"[SKIP CLEAN] {book_id} already processed")
                continue

            if not input_html.exists():
                missing.append(book_id)
                continue

            html = detect_encoding_and_read(input_html)
            if html is None:
                missing.append(book_id)
                continue

            clean_and_save(
                gt_id=book_id,
                raw_text=extract_raw_text(html),
                normalize=True,
                output_file=output_txt,
                log_file=log_file,
            )
            processed += 1

        logger.info(f"Processed {processed} books for split {split}")
        if missing:
            logger.warning(f"{len(missing)} missing/unreadable books in {split}")

    logger.info("Download and cleaning completed.")

    # -------------------
    # OPTIONAL JSONL
    # -------------------
    if not args.write_as_jsonl:
        return

    output_folder = args.output_dir / "jsonl"
    output_folder.mkdir(parents=True, exist_ok=True)

    for splitpath in ANNOTATIONS_FOLDER.glob("*.jsonl"):
        split = splitpath.stem
        with splitpath.open("r", encoding="utf-8") as f:
            split_data = [json.loads(line) for line in f]

        with (output_folder / f"{split}.jsonl").open("w", encoding="utf-8") as f_out:
            for item in tqdm(split_data, desc=f"Writing {split}"):
                book_id = item["gutenberg_id"]
                cleaned_path = args.output_dir / split / f"{book_id}.cleaned.txt"
                item["text"] = (
                    cleaned_path.read_text(encoding="utf-8")
                    if cleaned_path.exists()
                    else None
                )
                f_out.write(json.dumps(item) + "\n")

    logger.info(f"JSONL files written to {output_folder}")


if __name__ == "__main__":
    args = ScriptArgs().parse_args()
    main(args)
