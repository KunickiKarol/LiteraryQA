<div align="center"><img src="assets/literaryqa_icon.png" width="700"></div>

<div align="center">

[![Conference](http://img.shields.io/badge/EMNLP-2025-4b44ce.svg)](https://2025.aclweb.org/)
[![Paper](http://img.shields.io/badge/paper-ACL--anthology-B31B1B.svg)](https://arxiv.org/abs/2510.13494)
[![arXiv](https://img.shields.io/badge/arXiv-paper-008080.svg)](https://arxiv.org/abs/2510.13494) 
[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-FCD21D)](https://huggingface.co/datasets/sapienzanlp/LiteraryQA)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-green.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
</div>


##  📖 Description
This repository contains the official code for the EMNLP 2025 main conference paper: [LiteraryQA: Towards Effective Evaluation of Long-document Narrative QA](https://arxiv.org/abs/2510.13494) by [Tommaso Bonomo](https://www.linkedin.com/in/tommaso-bonomo/)\*, [Luca Gioffré](https://www.linkedin.com/in/luca-gioffre/)\* and [Roberto Navigli](https://www.linkedin.com/in/robertonavigli/).

The dataset is available at this [🤗 Hugging Face dataset](https://huggingface.co/datasets/sapienzanlp/LiteraryQA).
If you rather download the data manually, or if you want to run evaluations on your own models' predictions, please follow the instructions below.

## ⚠️ Project Gutenberg License Disclaimer

LiteraryQA is based on books from Project Gutenberg, which are publicly available under the [Project Gutenberg License](https://www.gutenberg.org/policy/license.html).
This license holds for users located in the United States, where the books are in the public domain.

We do not distribute the original text of the books, rather our dataset consists of a script that downloads and preprocesses the books from Project Gutenberg.
**Users are responsible for checking the copyright status of each book in their country**.


## 💾 Local data

### ⚙️ Setup and download

Clone the repository:
```bash
git clone https://github.com/sapienzanlp/LiteraryQA.git
cd LiteraryQA
```

We recommend using [uv](https://docs.astral.sh/uv/getting-started/installation/) as your Python package manager to quickly run our scripts.
You can install it with:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

To download and clean the books from Project Gutenberg, run:
```bash
uv run scripts/download_and_clean_books.py

options:
  --output_dir <path> = "data/literaryqa"  # Directory to save downloaded books
  --write_as_jsonl <bool> = False # Whether to write the complete dataset as JSONL files in output_dir/jsonl
```

<details>
<summary>Using <code>venv</code> instead of <code>uv</code></summary>

If you rather use `venv` and `pip`, you can create a virtual environment and install the required packages with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then, you can run the download script with:
```bash
python scripts/download_and_clean_books.py --output_dir data/literaryqa
```
</details>

### 📋 Data format
LiteraryQA is a filtered and improved version of [NarrativeQA](https://arxiv.org/abs/1712.07040). 
Here is a sample of the dataset:

```python
{
    "document_id": "9562ea781e95c048df96f528a2a8272721cde3a7",  # (str) i.e., NarrativeQA ID of the document
    "gutenberg_id": "32154",  # (str) i.e., key of the book in Project Gutenberg
    "split": "test",  # (str) i.e., in which split the book is found
    "title": "The Variable Man",  # (str) i.e., title of the book
    "text": "THE VARIABLE MAN\nBY PHILIP K. DICK\nILLUSTRATED BY EBEL\nHe fixed things—clocks, refrigerators, vidsen...",  # (str) i.e., full text of the book
    "summary": "The Terran system is growing and expanding all the time. But an old and corrupt Centaurian Empire is...",  # (str) i.e., summary of the book
    "qas": [  # (list) i.e., list of question-answer pairs associated with the book
        {
            "question": "Why is Terra at war with Proxima Centauri?",  # (str) i.e., question about the book
            "answers": [
                "Because they will not give Terra the room to expand their empire.",
                "The Centaurian Empire will not let humans from Terra grow out of their current empire.",
            ],  # (list) i.e., list of reference answers to the question
            "is_question_modified": False,  # (bool) i.e., whether the question was modified by an LLM or a human annotator
            "is_answer_modified": [
                False,
                False,
            ],  # (list) i.e., whether each of the reference answers was modified by an LLM or a human annotator
        },
        ...,
    ],
    "metadata": {  # (dict) i.e., additional metadata about the book
        "author": "Philip K. Dick",  # (str) i.e., author of the book
        "publication_date": "-",  # (str) i.e., publication date of the book
        "genre_tags": "novella;literary work;sci-fi;",  # (str) i.e., genre tags associated with the book
        "text_urls": "http://www.gutenberg.org/ebooks/32154.txt.utf-8",  # (str) i.e., original URL to the full text of the book
        "summary_urls": "http://en.wikipedia.org/wiki/The_Variable_Man",  # (str) i.e., original URL to the summary of the book
    },
}
```

## 📊 Evaluation

To run the evaluation of your model's predictions, you must have a file in JSONL format containing the predictions and the reference answers.
The simplest schema for each entry must be:
```python
{
    "prediction": "your model's answer here",  # (str) i.e., your model's predicted answer to the question
    "answers": [  # (list) i.e., list of reference answers to the question
        "first reference answer here",
        "second reference answer here",
    ],
    # Optional fields if using LLM-as-a-Judge:
    "question": "the question",  # (str) i.e., the question asked to the model,
    "title": "the title of the book",  # (str) i.e., the title of the book, to provide context to the LLM judge
    "summary": "the summary of the book",  # (str) i.e., the summary of the book, used in the summary-based evaluation
}
```
We provide the predictions of the systems tested in the paper in the `data/predictions/` folder for your reference.

To run the evaluation, first update the environment to use the necessary packages:
```bash
uv sync --extra judging
```

<details>
<summary>If using <code>pip</code> inside of a virtual environment instead of <code>uv</code></summary>

You can install the extra packages with:
```bash
pip install -e ".[judging]"
```
</details>

Then, use the following command:
```bash
uv run scripts/evaluate_predictions.py --predictions_file <path_to_your_predictions_file>
```


## 📝 Citation
This work has been published at EMNLP 2025 (main conference). If you use any artifact, please cite our paper as follows:

```bibtex
@misc{bonomo2025literaryqa,
      title={{LiteraryQA: Towards Effective Evaluation of Long-document Narrative QA}}, 
      author={Tommaso Bonomo and Luca Gioffré and Roberto Navigli},
      year={2025},
      eprint={2510.13494},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2510.13494}, 
}
```


## 📄 License

The data and software are licensed under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
