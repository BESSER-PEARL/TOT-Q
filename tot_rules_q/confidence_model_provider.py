"""Confidence-model provider interface: decouples the HITL workflow from how the
initial model and its per-element confidence scores are produced."""
import os
import sys
import subprocess
from abc import ABC, abstractmethod
from os.path import dirname, join, abspath, basename

from convert_tot_to_rbagent import get_domain_models

PROJECT_ROOT = dirname(dirname(abspath(__file__)))


class ConfidenceModelProvider(ABC):
    """Produces (domain_model, domain_model_alternatives) with a score per element."""

    @abstractmethod
    def build(self, domain_file, session_id=None):
        raise NotImplementedError

    def output_artifact(self, domain_file):
        return None

    def parse_tree(self, tree_path):
        raise NotImplementedError(f"{type(self).__name__} does not support parse_tree.")


class ToTModelProvider(ConfidenceModelProvider):
    """ToT4DM provider: generates the ToT tree and parses it into scored models."""

    DEFAULT_MODEL = "asocclass_3lev_unc.dmtot"

    def __init__(self, model_file=None, project_root=None):
        self.model_file = model_file or self.DEFAULT_MODEL
        self.project_root = project_root or PROJECT_ROOT

    def tree_path(self, domain_file):
        model_stem = self.model_file.replace(".dmtot", "")
        domain_stem = basename(domain_file).replace(".txt", "")
        return join(self.project_root, f"{model_stem}_{domain_stem}.json")

    def output_artifact(self, domain_file):
        return self.tree_path(domain_file)

    def _generate_tree(self, domain_file):
        subprocess.run(
            [sys.executable, "dsl/run.py", "--model", self.model_file, "--domain", basename(domain_file)],
            capture_output=True,
            text=True,
            check=True,
            cwd=self.project_root,
        )
        return self.tree_path(domain_file)

    def parse_tree(self, tree_path):
        return get_domain_models(tree_path)

    def build(self, domain_file, session_id=None):
        return self.parse_tree(self._generate_tree(domain_file))


_PROVIDERS = {
    "tot": ToTModelProvider,
}


def get_provider(name=None, **kwargs):
    """Return the provider selected by `name` or MODEL_PROVIDER (default 'tot')."""
    name = (name or os.getenv("MODEL_PROVIDER", "tot")).strip().lower()
    try:
        provider_cls = _PROVIDERS[name]
    except KeyError:
        valid = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"Unknown MODEL_PROVIDER: {name!r}. Valid options: {valid}.")
    return provider_cls(**kwargs)
