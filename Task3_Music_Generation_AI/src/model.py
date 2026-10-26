"""
Deep Learning Music Generation Model Architecture (Stacked LSTM)
Built with PyTorch. Learns sequential musical note dependencies and predicts next notes.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn


class MusicLSTM(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 64,
        hidden_dim: int = 256,
        num_layers: int = 2,
        dropout: float = 0.25
    ):
        super(MusicLSTM, self).__init__()
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # Token embedding layer
        self.embedding = nn.Embedding(vocab_size, embedding_dim)

        # Multi-layer stacked LSTM
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True
        )

        self.batch_norm = nn.BatchNorm1d(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        # Fully connected projection to vocabulary distribution
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        # x shape: [batch_size, seq_len]
        embeds = self.embedding(x) # [batch_size, seq_len, embedding_dim]
        lstm_out, hidden = self.lstm(embeds, hidden) # lstm_out: [batch_size, seq_len, hidden_dim]

        # Extract last time step output
        last_step = lstm_out[:, -1, :] # [batch_size, hidden_dim]

        if last_step.size(0) > 1:
            normed = self.batch_norm(last_step)
        else:
            normed = last_step

        dropped = self.dropout(normed)
        logits = self.fc(dropped) # [batch_size, vocab_size]

        return logits, hidden


if __name__ == "__main__":
    vocab_sz = 92
    model = MusicLSTM(vocab_size=vocab_sz)
    dummy_input = torch.randint(0, vocab_sz, (4, 16)) # batch_size 4, seq_length 16
    output, _ = model(dummy_input)
    print("Model initialized successfully.")
    print(f"Input shape: {dummy_input.shape} -> Output logits shape: {output.shape}")
