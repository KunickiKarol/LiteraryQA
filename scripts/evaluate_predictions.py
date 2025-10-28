import importlib
import json
from pathlib import Path

from loguru import logger
from tap import Tap

from literaryqa.ngram_metrics import exact_match_score, f1_score, meteor_score, rouge_l_score
from literaryqa.prometheus import ContextType, evaluate_with_prometheus

_MODEL_MAPPING = {"prometheus": "prometheus-eval/prometheus-7b-v2.0"}


class ScriptArgs(Tap):
    predictions_file: Path  # Path to the predictions JSONL file
    output_file: Path | None = None  # Path to save the computed metrics
    judge_model: str | None = None  # Model name for judging (if needed). If None, no judging is performed.
    judge_setting: ContextType = "references"  # Context for judging

    def process_args(self):
        if self.output_file is not None:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)

        if self.judge_model is not None:
            try:
                importlib.import_module("prometheus_eval")
            except ImportError:
                raise ImportError(
                    "prometheus-eval is not installed. Please install it through 'uv sync --extra judging'"
                )
            self.judge_model = _MODEL_MAPPING.get(self.judge_model, self.judge_model)


def main(args: ScriptArgs) -> None:
    logger.info("Starting evaluation of predictions...")

    # Load predictions
    with args.predictions_file.open("r", encoding="utf-8") as f:
        predictions_data = [json.loads(line) for line in f]
    logger.info(f"Loaded {len(predictions_data)} predictions from {args.predictions_file}")

    # Check schema of predictions_data
    for item in predictions_data:
        if "prediction" not in item or "answers" not in item:
            raise ValueError("Each item in predictions file must contain 'prediction' and 'answers' fields.")
        if not isinstance(item["answers"], list):
            raise ValueError("'answers' field must be a list of reference answers.")

    # Extract predictions and references
    predictions = [item["prediction"] for item in predictions_data]
    references = [item["answers"] for item in predictions_data]

    # Compute ngram metrics
    em = exact_match_score(predictions, references)
    f1 = f1_score(predictions, references)
    rouge_l = rouge_l_score(predictions, references)
    meteor = meteor_score(predictions, references)
    logger.info("Computed n-gram based metrics.")

    metrics = {
        "exact_match": em,
        "f1": f1,
        "rouge_l": rouge_l,
        "meteor": meteor,
    }

    # If judge_model is specified, perform evaluation with Prometheus
    if args.judge_model is not None:
        logger.info(f"Evaluating with Prometheus using model {args.judge_model}...")
        try:
            questions = [item["question"] for item in predictions_data]
            titles = [item["title"] for item in predictions_data]
            summaries = [item["summary"] for item in predictions_data]
        except KeyError:
            raise ValueError(
                "To evaluate predictions with Prometheus, each sample must also contain 'question', 'title', and 'summary' fields."
            )

        prometheus_scores = evaluate_with_prometheus(
            predictions=predictions,
            references=references,
            questions=questions,
            titles=titles,
            summaries=summaries,
            context=args.judge_setting,
            judge_model=args.judge_model,
        )
        avg_prometheus_score = sum(prometheus_scores) / len(prometheus_scores)
        metrics["prometheus_score"] = avg_prometheus_score

    # Output results
    if args.output_file:
        with args.output_file.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=4)
    else:
        logger.info("Evaluation metrics:")
        logger.info(json.dumps(metrics, indent=4))


if __name__ == "__main__":
    args = ScriptArgs().parse_args()
    main(args)
