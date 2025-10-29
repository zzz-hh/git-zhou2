# encoding:utf-8
import torch
import torch.nn as nn
import torch.nn.functional as F
from opacus.validators import ModuleValidator
from fediux.utils.logger_util import logger


class TextCNN(nn.Module):
    def __init__(self, vocab_size, embedding_dim, num_filters, dropout, output_dim):
        super().__init__()
        self.filter_sizes = [3, 4, 5]
        self.num_filters = num_filters
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        nn.init.uniform_(self.embedding.weight, -0.1, 0.1)

        self.convs = nn.ModuleList([
            nn.Conv2d(1, self.num_filters, (fs, embedding_dim)) 
            for fs in self.filter_sizes
        ])
        for conv in self.convs:
            nn.init.kaiming_normal_(conv.weight, mode='fan_out', nonlinearity='relu')
            nn.init.constant_(conv.bias, 0)

        self.bn = nn.BatchNorm1d(len(self.filter_sizes) * self.num_filters)

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(len(self.filter_sizes) * self.num_filters, output_dim)
        nn.init.normal_(self.fc.weight, mean=0, std=0.01)
        nn.init.constant_(self.fc.bias, 0)

    def forward(self, x):
        x = self.embedding(x)  # [batch_size, seq_len, emb_dim]
        x = x.unsqueeze(1)    # [batch_size, 1, seq_len, emb_dim]
        
        pooled_outputs = []
        for conv in self.convs:
            conv_out = F.relu(conv(x))      # [batch_size, num_filters, seq_len - fs + 1, 1]
            conv_out = conv_out.squeeze(3)   # [batch_size, num_filters, seq_len - fs + 1]
            pooled = F.max_pool1d(conv_out, conv_out.size(2)).squeeze(2)  # [batch_size, num_filters]
            pooled = self.dropout(pooled)
            pooled_outputs.append(pooled)
            
        cat = torch.cat(pooled_outputs, 1)  # [batch_size, num_filters * len(filter_sizes)]
        cat = self.bn(cat)
        cat = self.dropout(cat)
        return self.fc(cat)
    

def create_model(method, vocab_size, embedding_dim, num_filters, dropout, output_dim, device):
    model = TextCNN(vocab_size, embedding_dim, num_filters, dropout, output_dim)

    if method == 'DPSGD':
        errors = ModuleValidator.validate(model, strict=False)
        if len(errors) != 0:
            logger.error(errors)
            model = ModuleValidator.fix(model)
    logger.info(model)
    return model.to(device)
