import sys
from typing import Literal

from loguru import logger

# Check if prometheus_eval is installed
# Won't be used if not installed, as same check is done in evaluate_predictions.py
try:
    from prometheus_eval import PrometheusEval
    from prometheus_eval.prompts import ABSOLUTE_PROMPT, SCORE_RUBRIC_TEMPLATE
    from prometheus_eval.vllm import VLLM
except ImportError:
    pass

PROMPTS = {
    "summary": {
        "instruction": "You are an expert narrative analyst tasked with evaluating candidate answers to questions about books. You are provided with the summary of the book to refer to as added context. Here is the summary of {title}:\n{summary}\n\nQuestion:\n{question}",
        "rubric": {
            "criteria": "How acceptable is the candidate answer EITHER compared to the reference answer OR validated against the summary?",
            "score1_description": "The candidate answer is completely wrong.",
            "score2_description": "The answer does not answer the original question, but there is some information related to the reference answer or summary.",
            "score3_description": "The candidate answer is partially correct, but it contains some errors, omits key information or adds major extra information.",
            "score4_description": "The candidate answer is correct but it includes minor details that cannot be verified against the reference or the summary.",
            "score5_description": "The candidate answer is either exactly identical to one of the reference answers or it is a paraphrase of a reference answer that does not alter its meaning.",
        },
    },
    "references": {
        "instruction": "You are an expert narrative analyst tasked with evaluating candidate answers to questions about books. Here is the question of the story {title}:\nQuestion:\n{question}",
        "rubric": {
            "criteria": "How acceptable is the candidate answer compared to the reference answer?",
            "score1_description": "The candidate answer is completely wrong.",
            "score2_description": "The answer does not answer the original question, but there is some information related to the reference answer or summary.",
            "score3_description": "The candidate answer is partially correct, but it contains some errors, omits key information or adds major extra information.",
            "score4_description": "The candidate answer is correct but it includes minor details that cannot be verified against the reference.",
            "score5_description": "The candidate answer is either exactly identical to one of the reference answers or it is a paraphrase of a reference answer that does not alter its meaning.",
        },
    },
}

# Constants
DEFAULT_MODEL = "prometheus-eval/prometheus-7b-v2.0"
DEFAULT_TENSOR_PARALLEL_SIZE = 1
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.0
DEFAULT_REPETITION_PENALTY = 1.03
DEFAULT_BEST_OF = 1
DEFAULT_SEED = 42

ContextType = Literal["references", "summary"]


def _check_prometheus_available() -> None:
    """Check if prometheus_eval is available and raise a helpful error if not."""
    if "prometheus_eval" not in sys.modules:
        raise ImportError("prometheus-eval is not installed. Please install it with: pip install prometheus-eval")


def get_judge(
    model_name: str = DEFAULT_MODEL, tensor_parallel_size: int = DEFAULT_TENSOR_PARALLEL_SIZE
) -> PrometheusEval:
    """Initialize and return a PrometheusEval judge instance.

    Args:
        model_name: The model to use for evaluation.
        tensor_parallel_size: Number of GPUs to use for tensor parallelism.

    Returns:
        PrometheusEval: Initialized judge instance.

    Raises:
        ImportError: If prometheus-eval is not installed.
    """
    _check_prometheus_available()
    model = VLLM(model=model_name, tensor_parallel_size=tensor_parallel_size)
    judge = PrometheusEval(model=model, absolute_grade_template=ABSOLUTE_PROMPT)
    return judge


def get_rubric(context: ContextType) -> str:
    """Return the rubric string based on the context.

    Args:
        context: The evaluation context ('references' or 'summary').

    Returns:
        str: Formatted rubric string.

    Raises:
        KeyError: If context is not valid.
    """
    if context not in PROMPTS:
        raise ValueError(f"Invalid context: {context}. Must be 'references' or 'summary'.")
    rubric_map = PROMPTS[context]["rubric"]
    rubric = SCORE_RUBRIC_TEMPLATE.format(**rubric_map)
    return rubric


def _build_instruction(
    context: ContextType,
    title: str,
    question: str,
    summary: str | None = None,
) -> str:
    """Build instruction string for a single evaluation."""
    template = PROMPTS[context]["instruction"]
    if context == "summary":
        if summary is None:
            raise ValueError("Summary is required when context is 'summary'.")
        return template.format(summary=summary, title=title, question=question)
    return template.format(title=title, question=question)


def _validate_inputs(
    predictions: list[str],
    references: list[list[str]],
    questions: list[str],
    titles: list[str],
    summaries: list[str] | None,
    context: ContextType,
) -> None:
    """Validate input lists have consistent lengths and required data."""
    n = len(predictions)
    if not all(len(lst) == n for lst in [references, questions, titles]):
        raise ValueError(
            "All input lists must have the same length. "
            f"Got predictions={n}, references={len(references)}, "
            f"questions={len(questions)}, titles={len(titles)}"
        )

    if context == "summary":
        if summaries is None:
            raise ValueError("Summaries must be provided when context is 'summary'.")
        if len(summaries) != n:
            raise ValueError(f"Summaries length ({len(summaries)}) must match predictions length ({n}).")


def evaluate_with_prometheus(
    predictions: list[str],
    references: list[list[str]],
    questions: list[str],
    titles: list[str],
    summaries: list[str] | None = None,
    context: ContextType = "references",
    judge_model: str = DEFAULT_MODEL,
    tensor_parallel_size: int = DEFAULT_TENSOR_PARALLEL_SIZE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[list[str], list[int]]:
    """Evaluate predictions using PrometheusEval.

    Args:
        predictions: List of model predictions.
        references: List of lists of reference answers.
        questions: List of questions corresponding to the predictions.
        titles: List of titles corresponding to the predictions.
        summaries: List of summaries (required if context is "summary").
        context: Evaluation context, either "references" or "summary".
        judge_model: Model name for judging.
        tensor_parallel_size: Tensor parallel size for the model.
        max_tokens: Maximum tokens for the response.
        temperature: Temperature for sampling.

    Returns:
        tuple: (feedbacks, scores) where:
            - feedbacks: List of feedback strings from the judge
            - scores: List of integer scores from the judge

    Raises:
        ValueError: If inputs are invalid or inconsistent.
        ImportError: If prometheus-eval is not installed.
    """
    _check_prometheus_available()
    _validate_inputs(predictions, references, questions, titles, summaries, context)
    logger.info("Starting evaluation with PrometheusEval")

    # Initialize judge
    judge = get_judge(model_name=judge_model, tensor_parallel_size=tensor_parallel_size)
    logger.info("Initialized judge for PrometheusEval")

    # Build instructions for each prediction
    instructions = [
        _build_instruction(context, titles[i], questions[i], summaries[i] if summaries else None)
        for i in range(len(predictions))
    ]
    logger.info(f"Built {len(instructions)} instructions for PrometheusEval")

    # Prepare reference answers as concatenated strings
    reference_answers = ["\n".join(refs).strip() for refs in references]

    rubric = get_rubric(context)

    logger.info("Starting absolute grading with PrometheusEval")
    feedbacks, scores = judge.absolute_grade(
        instructions=instructions,
        responses=predictions,
        reference_answers=reference_answers,
        rubric=rubric,
        params={
            "max_tokens": max_tokens,
            "repetition_penalty": DEFAULT_REPETITION_PENALTY,
            "best_of": DEFAULT_BEST_OF,
            "temperature": temperature,
            "seed": DEFAULT_SEED,
        },
    )
    logger.info("Completed absolute grading with PrometheusEval")
    return feedbacks, scores
