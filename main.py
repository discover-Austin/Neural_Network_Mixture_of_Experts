import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import matplotlib.pyplot as plt
import numpy as np
from moe import MixtureOfExperts, MoETrainer

def main():
    # Create some synthetic data
    def generate_synthetic_data(num_samples=1000):
        # Create data with different patterns for experts to specialize in
        X = torch.randn(num_samples, 10)  # 10-dimensional input
        
        # Create targets with different patterns
        # Pattern 1: First 5 dimensions are important
        y1 = torch.sin(X[:, :5].sum(dim=1))
        # Pattern 2: Last 5 dimensions are important
        y2 = torch.cos(X[:, 5:].sum(dim=1))
        # Combine patterns
        y = y1 + y2
        
        return X, y.unsqueeze(1)  # Add output dimension

    # Generate data
    X_train, y_train = generate_synthetic_data(1000)
    X_val, y_val = generate_synthetic_data(200)

    # Create data loaders
    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)

    # Initialize model
    model = MixtureOfExperts(
        input_dim=10,           # Input dimension
        hidden_dims=[64, 64],   # Hidden layers in each expert
        output_dim=1,           # Output dimension
        num_experts=4,          # Number of experts
        gating_hidden_dim=32    # Hidden dim for gating network
    )

    # Initialize trainer
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    task_loss_fn = nn.MSELoss()
    trainer = MoETrainer(
        model=model,
        optimizer=optimizer,
        task_loss_fn=task_loss_fn,
        load_balance_coef=0.1
    )

    # Training loop
    num_epochs = 50
    train_losses = []
    val_losses = []
    expert_utilization_history = []

    for epoch in range(num_epochs):
        # Training
        epoch_losses = []
        for x_batch, y_batch in train_loader:
            losses = trainer.train_step(x_batch, y_batch)
            epoch_losses.append(losses['total_loss'])
        
        # Record training loss
        train_loss = sum(epoch_losses) / len(epoch_losses)
        train_losses.append(train_loss)
        
        # Validation
        val_loss = trainer.evaluate(val_loader)
        val_losses.append(val_loss)
        
        # Record expert utilization
        expert_utilization_history.append(
            model.get_expert_utilization_rates().cpu().numpy()
        )
        
        # Print progress
        if (epoch + 1) % 5 == 0:
            print(f"Epoch {epoch+1}/{num_epochs}")
            print(f"Train Loss: {train_loss:.4f}")
            print(f"Val Loss: {val_loss:.4f}")
            print("Expert Utilization:", 
                  model.get_expert_utilization_rates().numpy().round(3))
            print("-" * 50)

    # Plotting utilities
    def plot_training_curves(train_losses, val_losses):
        plt.figure(figsize=(10, 5))
        plt.plot(train_losses, label='Train Loss')
        plt.plot(val_losses, label='Validation Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_expert_utilization(expert_utilization_history):
        plt.figure(figsize=(10, 5))
        expert_utilization_history = np.array(expert_utilization_history)
        for i in range(model.num_experts):
            plt.plot(expert_utilization_history[:, i], 
                    label=f'Expert {i+1}')
        plt.xlabel('Epoch')
        plt.ylabel('Utilization Rate')
        plt.title('Expert Utilization Over Time')
        plt.legend()
        plt.grid(True)
        plt.show()

    # Plot results
    plot_training_curves(train_losses, val_losses)
    plot_expert_utilization(expert_utilization_history)

    # Test model inference
    def test_model_inference(model, x):
        model.eval()
        with torch.no_grad():
            output = model(x)
            # Get expert assignments
            gate_weights = model.gate(x)
            # Get expert with highest weight for each sample
            primary_experts = gate_weights.argmax(dim=1)
        return output, primary_experts

    # Test on some samples
    test_x = X_val[:5]
    predictions, expert_assignments = test_model_inference(model, test_x)
    print("\nTest Predictions:")
    print("Input Shape:", test_x.shape)
    print("Output Shape:", predictions.shape)
    print("Expert Assignments:", expert_assignments.numpy())

if __name__ == "__main__":
    main()