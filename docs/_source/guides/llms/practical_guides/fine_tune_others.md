# Fine-tune other models

After [collecting the responses](/guides/llms/practical_guides/collect_responses) from our `FeedbackDataset` we can start fine-tuning our basic models. Due to the customizability of the `FeedbackDataset`, this might require setting up a custom post-processing workflow but we will provide some good toy examples for the text classification task. We will add additional support for other tasks in the future.

Generally, this is as easy as one-two-three but does slightly differ per task.

1. First, we define a unification strategy for responses to `questions` we want to use.
2. Next, we then define a task-mapping. This mapping defines which `fields` and `questions` we want to use from our dataset for the downstream training task. These mappings are then used for retrieving data from a dataset and initializing the training.
3. Lastly, we initialize the `ArgillaTrainer` and forward the task mapping, unification strategies and training framework.

## Text classification

### Background

Text classification is a widely used NLP task where labels are assigned to text. Major companies rely on it for various applications. Sentiment analysis, a popular form of text classification, assigns labels like 🙂 positive, 🙁 negative, or 😐 neutral to text. Additionally, we distinguish between single- and multi-label text classification.

#### Single-label
Single-label text classification refers to the task of assigning a single category or label to a given text sample. Each text is associated with only one predefined class or category. For example, in sentiment analysis, a single-label text classification task would involve assigning labels such as "positive," "negative," or "neutral" to individual texts based on their sentiment.

#### Multi-label
Multi-label text classification is generally more complex than single-label classification due to the challenge of determining and predicting multiple relevant labels for each text. It finds applications in various domains, including document tagging, topic labeling, and content recommendation systems.

### Training

Data for the training text classification using our `FeedbackDataset` is defined by following three easy steps.

1. We need to define unification strategies a `RatingUnification`, a `LabelUnification` or a `MultiLabelUnification`.

2.  For this task, we assume we need a `text-label`-pair for defining a text classification task. We allow mapping for creating a `TrainingTaskMapingForTextClassification` by mapping `*Field` to a `text`-value and allow for mapping a `RatingUnification`, `LabelUnification` or a `MultiLabelUnification` to a `label`-value.

3.  We then define an `ArgillaTrainer` instance with support for "openai", "setfit", "peft", "spacy" and "transformers".

#### Unify responses

Argilla `*Question`s need to be [unified using a strategy](/guides/llms/practical_guides/collect_responses) and so do `RatingQuestions`s, `LabelQuestion`s and `MultiLabelQuestion`s. Therefore, we first need to define a `*QuestionUnification`, which takes one of the questions and one of their associated strategies.

````{note}
Note that `RatingQuestion`s can be unified using a "majority"-, "min"-, "max"- or "disagreement"-strategy. Both `LabelQuestion`s and `MultiLabelQuestion`s can be resolved using a "majority"-, or "disagreement"-strategy.
````

::::{tab-set}

:::{tab-item} RatingQuestion
```python
from argilla import RatingQuestion, RatingUnification

label_unification = RatingUnification(
    question=LabelQuestion(...),
    strategy="majority" # or "min", "max", "disagreement"
)
```
:::

:::{tab-item} LabelQuestion
```python
from argilla import LabelQuestion, LabelUnification

label_unification = LabelUnification(
    question=LabelQuestion(...),
    strategy="majority" # or "disagreement"
)
```
:::

:::{tab-item} MultiLabelQuestion
```python
from argilla import MultiLabelQuestion, MultiLabelUnification

label_unification = MultiLabelUnification(
    question=MultiLabelQuestion(...),
    strategy="majority" # or "disagreement"
)
```
:::

::::

#### Define a task mapping

After defining the `unfication`, we can now define our `TrainingTaskMapingForTextClassification`.

```python
from argilla import FeedbackDataset, TrainingTaskMapingForTextClassification

label_unification = ...
dataset = FeedbackDataset(...)
training_task_mapping = TrainingTaskMapingForTextClassification(
    text=dataset.field_by_name("my_text_field"),
    label=label_unification
)
```

#### Use ArgillaTrainer

Next, we can use our `FeedbackDataset` and `TrainingTaskMapingForTextClassification` to initialize our `argilla.ArgillaTrainer`. We support the frameworks "openai", "setfit", "peft", "spacy" and "transformers".

````{note}
This is a newer version and can be imported via `from argilla import ArgillaTrainer`. The old trainer can be imported via `from argilla.training import ArgillaTrainer`. Our docs, contain some [additional information on usage of the ArgillaTrainer](/guides/train_a_model).
````

```python
from argilla import ArgillaTrainer

dataset = ...
training_task_mapping = ...
trainer = ArgillaTrainer(
    dataset=dataset,
    training_task_mapping=training_task_mapping,
    framework="setfit",
    fetch_records=False
)
trainer.update_config(num_train_epochs=2)
trainer.train(output_dir="my_awesone_model")
```

````{note}
The `FeedbackDataset` also allows for custom workflows via the `prepare_for_training()`-method.
```python
training_task_mapping = ...
dataset = ...
dataset.prepare_for_training(
    framework="setfit",
    training_task_mapping=training_task_mapping
)
```
````

### An end-to-end example

Underneath, you can also find an end-to-end example of how to use the `ArgillaTrainer`.

```python
import argilla as rg

dataset = rg.FeedbackDataset(
    guidelines="Add some guidelines for the annotation team here.",
    fields=[
        rg.TextField(name="text", title="Human prompt"),
    ],
    questions =[
        rg.LabelQuestion(
            name="relevant",
            title="Is the response relevant for the given prompt?",
            labels=["yes","no"],
            required=True,
        )
    ]
)
dataset.add_records(
    records=[
        rg.FeedbackRecord(
            fields={"text": "What is your favorite color?"},
            responses=[{"values": {"relevant": {"value": "no"}}}]
        ),
        rg.FeedbackRecord(
            fields={"text": "What do you think about the new iPhone?"},
            responses=[{"values": {"relevant": {"value": "yes"}}}]
        ),
        rg.FeedbackRecord(
            fields={"text": "What is your feeling about the technology?"},
            responses=[{"values": {"relevant": {"value": "yes"}}},
                       {"values": {"relevant": {"value": "no"}}},
                       {"values": {"relevant": {"value": "yes"}}}]
        ),
        rg.FeedbackRecord(
            fields={"text": "When do you expect to buy a new phone?"},
            responses=[{"values": {"relevant": {"value": "no"}}},
                       {"values": {"relevant": {"value": "yes"}}}]
        )

    ]
)

label_unification = rg.LabelQuestionUnification(
    question=dataset.question_by_name("relevant"),
    strategy="majority"
)

training_task_mapping = rg.TrainingTaskMapingForTextClassification(
    text=dataset.field_by_name("text"),
    label=label_unification
)

trainer = rg.ArgillaTrainer(
    dataset=dataset,
    training_task_mapping=training_task_mapping,
    framework="setfit",
    fetch_records=False
)
trainer.update_config(num_train_epochs=2)
trainer.train(output_dir="my_awesone_model")
```

