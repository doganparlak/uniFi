from abc import ABC, abstractmethod


class Agent(ABC):

    @abstractmethod
    def train_model(self, *args, **kwargs):
        pass

    @abstractmethod
    def predict(self, *args, **kwargs):
        pass

    @abstractmethod
    def save_model(self, *args, **kwargs):
        pass

    @abstractmethod
    def load_model(self, *args, **kwargs):
        pass
