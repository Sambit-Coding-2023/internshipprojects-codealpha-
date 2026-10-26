"""
Training Script for Task 3: Deep Learning Music Generation
Trains the Stacked LSTM neural network on processed MIDI sequences and saves the trained weights.
"""

from pathlib import Path
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

try:
    from .midi_processor import MidiProcessor
    from .model import MusicLSTM
except ImportError:
    from midi_processor import MidiProcessor
    from model import MusicLSTM


def train_music_model(
    epochs: int = 35,
    batch_size: int = 32,
    seq_length: int = 16,
    lr: float = 0.003,
    hidden_dim: int = 256,
    embedding_dim: int = 64
):
    print("=" * 65, flush=True)
    print("           TRAINING DEEP LEARNING MUSIC GENERATOR (LSTM)         ", flush=True)
    print("=" * 65, flush=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Hardware Compute Device: {device}", flush=True)

    # 1. Parse MIDI and prepare dataset
    processor = MidiProcessor()
    print("Loading / parsing MIDI dataset...", flush=True)
    notes = processor.parse_all_midi()
    note_to_int, int_to_note = processor.build_vocabulary(notes)
    vocab_size = len(note_to_int)
    print(f"Total Note Tokens: {len(notes)} | Vocabulary Size: {vocab_size} unique notes/chords", flush=True)

    network_input, network_output = processor.prepare_sequences(notes, seq_length=seq_length)
    print(f"Total Sequence Training Pairs: {len(network_input)}", flush=True)

    # 2. Convert to PyTorch Tensors & DataLoader
    X_tensor = torch.tensor(network_input, dtype=torch.long)
    y_tensor = torch.tensor(network_output, dtype=torch.long)

    dataset = TensorDataset(X_tensor, y_tensor)
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 3. Initialize Model, Loss, Optimizer
    model = MusicLSTM(
        vocab_size=vocab_size,
        embedding_dim=embedding_dim,
        hidden_dim=hidden_dim,
        num_layers=2,
        dropout=0.25
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # 4. Training Loop
    start_time = time.time()
    best_loss = float("inf")

    model.train()
    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        correct = 0
        total = 0

        for batch_x, batch_y in data_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            logits, _ = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()

            nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()

            epoch_loss += loss.item() * batch_x.size(0)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == batch_y).sum().item()
            total += batch_y.size(0)

        scheduler.step()
        avg_loss = epoch_loss / total
        accuracy = (correct / total) * 100

        if avg_loss < best_loss:
            best_loss = avg_loss

        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] - Loss: {avg_loss:.4f} | Accuracy: {accuracy:.1f}%", flush=True)

    elapsed = time.time() - start_time
    print(f"Training completed in {elapsed:.2f} seconds. Best Loss: {best_loss:.4f}", flush=True)

    # 5. Save Model Checkpoint
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = models_dir / "music_lstm.pth"

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "vocab_size": vocab_size,
        "embedding_dim": embedding_dim,
        "hidden_dim": hidden_dim,
        "seq_length": seq_length,
        "best_loss": best_loss
    }
    torch.save(checkpoint, checkpoint_path)
    print(f"Model saved successfully to: {checkpoint_path}", flush=True)

    return checkpoint_path


if __name__ == "__main__":
    train_music_model()
