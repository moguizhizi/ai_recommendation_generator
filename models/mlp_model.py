import torch
import torch.nn as nn
import numpy as np
import joblib

from src.models.base_model import BaseModel


class MLPNet(nn.Module):
    """
    简单 MLP 网络
    """

    def __init__(self, input_dim, hidden_dims=[128, 64], output_dim=1):
        super().__init__()

        layers = []
        prev_dim = input_dim

        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(nn.ReLU())
            prev_dim = h

        layers.append(nn.Linear(prev_dim, output_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class MLPModel(BaseModel):
    """
    MLP 回归模型
    """

    def __init__(self, params: dict | None = None):

        default_params = {
            "hidden_dims": [128, 64],
            "lr": 1e-3,
            "epochs": 20,
            "batch_size": 64,
        }

        if params:
            default_params.update(params)

        self.params = default_params

        self.model = None
        self.optimizer = None
        self.loss_fn = nn.MSELoss()

    # --------------------------------------------------
    # 训练
    # --------------------------------------------------

    def fit(self, X, y):

        X = np.array(X)
        y = np.array(y)

        input_dim = X.shape[1]

        if len(y.shape) == 1:
            output_dim = 1
            y = y.reshape(-1, 1)
        else:
            output_dim = y.shape[1]

        self.model = MLPNet(
            input_dim,
            self.params["hidden_dims"],
            output_dim,
        )

        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.params["lr"],
        )

        X_tensor = torch.tensor(X, dtype=torch.float32)
        y_tensor = torch.tensor(y, dtype=torch.float32)

        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)

        dataloader = torch.utils.data.DataLoader(
            dataset,
            batch_size=self.params["batch_size"],
            shuffle=True,
        )

        self.model.train()

        for epoch in range(self.params["epochs"]):

            total_loss = 0

            for batch_x, batch_y in dataloader:

                pred = self.model(batch_x)

                loss = self.loss_fn(pred, batch_y)

                self.optimizer.zero_grad()

                loss.backward()

                self.optimizer.step()

                total_loss += loss.item()

            avg_loss = total_loss / len(dataloader)

            print(f"Epoch {epoch+1}, loss={avg_loss:.4f}")

        return self

    # --------------------------------------------------
    # 预测
    # --------------------------------------------------

    def predict(self, X):

        self.model.eval()

        X = np.array(X)

        X_tensor = torch.tensor(X, dtype=torch.float32)

        with torch.no_grad():
            preds = self.model(X_tensor).numpy()

        return preds

    # --------------------------------------------------
    # 保存
    # --------------------------------------------------

    def save(self, path):

        torch.save(self.model.state_dict(), path)

    # --------------------------------------------------
    # 加载
    # --------------------------------------------------

    def load(self, path, input_dim, output_dim):

        self.model = MLPNet(
            input_dim,
            self.params["hidden_dims"],
            output_dim,
        )

        self.model.load_state_dict(torch.load(path))

        self.model.eval()

        return self
