
import inflect
import re
from difflib import SequenceMatcher
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 0.8))
high_confidence = float(os.getenv('HIGH_CONFIDENCE', confidence_threshold * 1.1))
low_confidence = float(os.getenv('LOW_CONFIDENCE', confidence_threshold / 2))

def correct_article(article, word):
    return inflect.engine().a(word).split()[0]

def plural(word):
    return inflect.engine().plural(word)

def split_camel_case(name):
    name = re.sub(r'^(is|has|can|should|was|were|get)(?=[A-Z])', '', name, flags=re.IGNORECASE)
    name = name[0].upper() + name[1:] if name else name
    words = re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', name)
    return ' '.join(words)

text_similarity = 0.8
def is_similar(name1, name2, text_similarity=0.8):
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio() > text_similarity

def name_format(str_name):
    checklist = ['abstract', 'Abstract']
    for c in checklist:
        str_name = str_name.replace(c, "")
    str_name = str_name.strip()
    #str_name = str_name.capitalize()
    str_name = str_name[0].upper() + str_name[1:] if str_name else str_name
    return str_name

class ConfigurationMetadata:
    def __init__(self, predicted, alternative_1_score: float = 0.0, alternative_2_score: float = 0.0):
        self.alternative_1_score = alternative_1_score
        self.alternative_2_score = alternative_2_score
        self.predicted = predicted
        self.order_score = alternative_1_score if predicted == "alternative_1" else alternative_2_score
        #patch enum vs subclass order_score wrong scale
        if self.order_score > 1: self.order_score = self.order_score/100
        self.implemented = ""


    def set_alternative_1_score(self, score: float) -> None:
        self.alternative_1_score = score
    
    def set_alternative_2_score(self, score: float) -> None:
        self.alternative_2_score = score

    def get_alternative_1_score(self) -> float:
        s = None
        if self.alternative_1_score:
            s = round(self.alternative_1_score,2)
        return s

    def get_alternative_2_score(self) -> float:
        s = None
        if self.alternative_2_score:
            s = round(self.alternative_2_score,2)
        return s

    def get_order_score(self) -> float:
        s = round(self.order_score,2)
        return s

    def __repr__(self):
        alt1 = f"{self.get_alternative_1_score()}" if self.alternative_1_score else f"None"
        alt2 = f"{self.get_alternative_2_score()}" if self.alternative_2_score else f"None"
        pred1 = f"Alt1:{alt1} (P)" if self.predicted == "alternative_1" else f"Alt1:{alt1}"
        pred2 = f"Alt2:{alt2} (P)" if self.predicted == "alternative_2" else f"Alt2:{alt2}"
        return f"{pred1} :: {pred2}"
    
class MetadataMixin:
    def __init__(self, *args, **kwargs):
        self._metadata: Optional[ConfigurationMetadata] = None
        super().__init__(*args, **kwargs)

    @property
    def metadata(self) -> ConfigurationMetadata:
        if self._metadata is None:
            self._metadata = ConfigurationMetadata()
        return self._metadata

    @metadata.setter
    def metadata(self, value: ConfigurationMetadata):
        self._metadata = value

    def set_metadata(self, predicted, alternative_1_score: float = 0.0, alternative_2_score: float = 0.0) -> None:
        self._metadata = ConfigurationMetadata(predicted, alternative_1_score, alternative_2_score)
    
    def get_metadata(self) -> ConfigurationMetadata:
        return self._metadata


class Configuration(MetadataMixin):
    def __init__(self, alternative_1 = None, alternative_2 = None, alternative_1_dm = None, alternative_2_dm = None, question = '', option_1 = '', option_2 = ''):
        self.alternative_1 = alternative_1  # e.g. an attribute
        self.alternative_2 = alternative_2  # e.g. a class
        self.alternative_1_dm = alternative_1_dm
        self.alternative_2_dm = alternative_2_dm
        self.question = question
        self.option_1 = option_1
        self.option_2 = option_2
        self.option_1_dm = None
        self.option_2_dm = None

    def add_alternative_1(self, alternative_1, alternative_1_dm):
        self.alternative_1 = alternative_1
        self.alternative_1_dm = alternative_1_dm

    def add_alternative_2(self, alternative_2, alternative_2_dm):
        self.alternative_2 = alternative_2
        self.alternative_2_dm = alternative_2_dm

    def add_option_1(self, option_1_dm):
        self.option_1_dm = option_1_dm

    def add_option_2(self, option_2_dm):
        self.option_2_dm = option_2_dm

    def update(self, domain_model, check_option):
        raise NotImplementedError("Subclasses must implement the update method")
    
    def set_confidence(self, configurations, alternative = True):
        raise NotImplementedError("Subclasses must implement the set confidence method")

    def update_confidence_model_element(self, element, confidence):
        if hasattr(element, '_metadata') and element.get_metadata():
            if element.get_metadata().get_score() < confidence:
                element.get_metadata().set_score(confidence)
        else: 
            element.set_metadata(confidence)

    def __repr__(self):
        text = f"Configuration(alternative_1={getattr(self.alternative_1, 'name', None)}, "
        text += f"alternative_2={getattr(self.alternative_2, 'name', None)})"
        #if self.alternative_1_dm: model_alt1 = f"{self.alternative_1_dm.generate_plantuml()}"
        #else: model_alt1 = f"No alternative found"
        #if self.alternative_2_dm: model_alt2 = f"{self.alternative_2_dm.generate_plantuml()}"
        #else: model_alt1 = f"No alternative found"
        model_alt1 = self.alternative_1_dm.generate_plantuml() if self.alternative_1_dm else "No alternative found"
        model_alt2 = self.alternative_2_dm.generate_plantuml() if self.alternative_2_dm else "No alternative found"
        return (f"Alternative 1:\n{model_alt1}\nAlternative2:\n{model_alt2}\n")
