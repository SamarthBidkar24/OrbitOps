import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, random_split
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
SAVED_DIR = BASE_DIR / "saved"

# Ensure saved dir exists
SAVED_DIR.mkdir(parents=True, exist_ok=True)

# ── Model Definition ──────────────────────────────────────────────────────────
class SpectraAutoencoder(nn.Module):
    def __init__(self, input_dim=41):
        super(SpectraAutoencoder, self).__init__()
        
        # Encoder: 41 -> 32 -> 16 -> 8
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.BatchNorm1d(8),
            nn.ReLU()
        )
        
        # Decoder: 8 -> 16 -> 32 -> 41
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 41),
            nn.Sigmoid() # Range 0-1
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

# ── Training Script ───────────────────────────────────────────────────────────
def train_autoencoder():
    # 1. Load Data
    print("[→] Loading spectral data...")
    X_processed = np.load(DATA_DIR / "X_processed.npy")
    scaler = joblib.load(SAVED_DIR / "scaler.pkl")
    
    # The instruction says final activation is Sigmoid and reflectances are in 0-2 range.
    # To match Sigmoid (0-1), we un-scale the data (getting ~0-2) and divide by 2.
    print("[→] Transforming data to 0-1 range for Sigmoid decoder...")
    X_raw = scaler.inverse_transform(X_processed)
    # Clamp to [0, 2] just in case of outliers, then scale to [0, 1]
    X_target = np.clip(X_raw, 0, 2.0) / 2.0
    
    # Convert to Tensors
    X_tensor = torch.FloatTensor(X_target)
    
    # Split: 85% train, 15% validation
    train_size = int(0.85 * len(X_tensor))
    val_size = len(X_tensor) - train_size
    train_dataset, val_dataset = random_split(X_tensor, [train_size, val_size])
    
    # DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # Model, Optimizer, Loss
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SpectraAutoencoder(input_dim=41).to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    criterion = nn.MSELoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
    
    # 2. Training Loop
    epochs = 200
    early_stop_patience = 20
    best_val_loss = float('inf')
    epochs_no_improve = 0
    
    history = {'train_loss': [], 'val_loss': []}
    
    print(f"[→] Training on {device}...")
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            outputs = model(batch)
            loss = criterion(outputs, batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                outputs = model(batch)
                loss = criterion(outputs, batch)
                val_loss += loss.item()
        val_loss /= len(val_loader)
        
        scheduler.step(val_loss)
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        
        if epoch % 10 == 0:
            print(f"Epoch {epoch}/{epochs} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")
            
        # Early Stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), SAVED_DIR / "autoencoder.pt")
            torch.save(model.encoder.state_dict(), SAVED_DIR / "encoder.pt")
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= early_stop_patience:
                print(f"Early stopping at epoch {epoch}")
                break
                
    # 3. Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(history['train_loss'], label='Train Loss')
    plt.plot(history['val_loss'], label='Val Loss')
    plt.title('Spectra Autoencoder Training History')
    plt.xlabel('Epoch')
    plt.ylabel('MSE Loss')
    plt.legend()
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.savefig(SAVED_DIR / "training_curve.png")
    print(f"[✓] Saved training curve to {SAVED_DIR / 'training_curve.png'}")
    
    # 4. Save Embeddings for ALL asteroids
    model.load_state_dict(torch.load(SAVED_DIR / "autoencoder.pt"))
    model.eval()
    with torch.no_grad():
        all_embeddings = model.encoder(X_tensor.to(device)).cpu().numpy()
        np.save(SAVED_DIR / "embeddings.npy", all_embeddings)
    print(f"[✓] Saved embeddings (shape: {all_embeddings.shape}) to {SAVED_DIR / 'embeddings.npy'}")
    
    # 5. Quick Sanity Check
    print("\n" + "="*40)
    print("SANITY CHECK (Original vs Reconstructed)")
    print("="*40)
    indices = np.random.choice(len(X_target), 3, replace=False)
    with torch.no_grad():
        for idx in indices:
            orig = X_tensor[idx].unsqueeze(0).to(device)
            recon = model(orig).cpu().numpy().flatten()
            orig = orig.cpu().numpy().flatten()
            
            # Re-scale back to 0-2 range for printing
            orig_scaled = orig * 2.0
            recon_scaled = recon * 2.0
            
            print(f"Asteroid Index: {idx}")
            # Check 5 wavelengths (indices 0, 10, 20, 30, 40)
            sample_indices = [0, 10, 20, 30, 40]
            print(f"  Orig:  {orig_scaled[sample_indices]}")
            print(f"  Recon: {recon_scaled[sample_indices]}")
            error = np.mean(np.abs(orig_scaled - recon_scaled))
            print(f"  Avg Error: {error:.4f} {'[PASS]' if error < 0.1 else '[FAIL]'}")
            print("-" * 20)

if __name__ == "__main__":
    train_autoencoder()
