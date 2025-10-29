# encoding:utf-8
import torch
import torch.nn as nn
from opacus.validators import ModuleValidator
from fediux.utils.logger_util import logger


class FastText(nn.Module):
    def __init__(self, vocab_size, embedding_dim, output_dim):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.fc = nn.Linear(embedding_dim, output_dim)

    def forward(self, x):
        embedded = self.embedding(x)  # [batch_size, seq_len, embedding_dim]
        pooled = embedded.mean(dim=1)  # [batch_size, embedding_dim]
        return self.fc(pooled)


def create_model(method, vocab_size, embedding_dim, output_dim, device):
    # 设置随机种子保证可重复性
    seed = 42
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    model = FastText(vocab_size, embedding_dim, output_dim)

    # validate model (DPSGD)
    if method == 'DPSGD':
        errors = ModuleValidator.validate(model, strict=False)
        if len(errors) != 0:
            logger.error(errors)
            model = ModuleValidator.fix(model)
    logger.info(model)
    return model.to(device)
