import torch
import torch.nn as nn
import pickle
from sklearn.model_selection import train_test_split

# Transformer Model
class GestureTransformer(nn.Module):
    def __init__(self, input_dim=126, hidden_dim=128, num_classes=11,
                 seq_length=30, num_layers=2, num_heads=4):
        super(GestureTransformer, self).__init__()
        self.embedding = nn.Linear(input_dim, hidden_dim)
        self.pos_encoding = nn.Parameter(torch.zeros(1, seq_length, hidden_dim))
        encoder_layer = nn.TransformerEncoderLayer(d_model=hidden_dim, nhead=num_heads)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.embedding(x)  # (batch_size, seq_length, hidden_dim)
        x = x + self.pos_encoding
        x = x.permute(1, 0, 2)  # (seq_length, batch_size, hidden_dim)
        x = self.transformer_encoder(x)
        x = x.mean(dim=0)  # (batch_size, hidden_dim)
        return self.fc(x)

def train():
    # Load Data
    with open('data_seq1.pickle', 'rb') as f:
        data_dict = pickle.load(f)

    data = torch.tensor(data_dict['data'], dtype=torch.float32)  # (num_samples, 30, 84)
    labels = torch.tensor(data_dict['labels'], dtype=torch.long)
    label_map = data_dict['label_map']
    num_classes = len(label_map)

    # Normalize
    data = data / data.max()

    # Train-Test Split
    x_train, x_test, y_train, y_test = train_test_split(
        data, labels, test_size=0.2, stratify=labels, random_state=42
    )

    # Training Setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = GestureTransformer(num_classes=num_classes).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    # Data Loader
    train_dataset = torch.utils.data.TensorDataset(x_train, y_train)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=32, shuffle=True)

    # Training Loop
    for epoch in range(50):
        model.train()
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            output = model(batch_x)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()
        print(f"Epoch {epoch+1}, Loss: {loss.item():.4f}")

    # Save Model
    torch.save(model.state_dict(), 'gesture_transformer_proxy.pth')
    print("✅ Model trained and saved to gesture_transformer_proxy.pth")

if __name__ == "__main__":
    train()
