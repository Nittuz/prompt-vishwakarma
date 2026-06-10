import json

from pv.generate.datagen import gen_examples
from pv.prompts.model import PromptVersion
from pv.runners.fake_runner import FakeRunner


def test_gen_examples_parses_input_json():
    def responder(messages, params):
        return {
            "examples": [
                {"input_json": json.dumps({"q": "what is 2+2"}), "reference": "4"},
                {"input_json": json.dumps({"q": "capital of France"}), "reference": "Paris"},
            ]
        }

    prompt = PromptVersion(name="p", user="Answer: {q}")
    out = gen_examples(FakeRunner(responder), prompt, n=2)
    assert len(out) == 2
    assert out[0].input == {"q": "what is 2+2"}
    assert out[0].reference == "4"
    assert out[0].id == "gen-1"


def test_gen_examples_skips_bad_json():
    def responder(messages, params):
        return {"examples": [{"input_json": "not json"}, {"input_json": "{\"q\": \"ok\"}"}]}

    out = gen_examples(FakeRunner(responder), PromptVersion(name="p", user="{q}"))
    assert len(out) == 1
    assert out[0].input == {"q": "ok"}
