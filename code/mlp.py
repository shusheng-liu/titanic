import pandas as pd
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader
from torch.utils.data.sampler import SubsetRandomSampler
from matplotlib import pyplot as plt

# Create custom class's to use pytorch's dataloader
# Each custom class needs __init__, __len__ and __getitem__ function
class train_data:
    
    def __init__(self):
        csv = pd.read_csv("data/train.csv", dtype={"Survived": np.float32})
        self.label = csv["Survived"].to_numpy()
        csv.drop(['PassengerId','Survived','Name','Ticket', 'Cabin'], axis=1, inplace=True)
        data = []
        for key, value in csv.iterrows():
            temp = []
            temp.append(np.float32(value.iat[0]))
            temp.append(np.float32(0)) if (value.iat[1] == "male") else temp.append(np.float32(1))
            temp.append(np.float32(0)) if (np.isnan(value.iat[2])) else temp.append(np.float32(value.iat[2]))
            temp.append(np.float32(value.iat[3]))
            temp.append(np.float32(value.iat[4]))
            if (value.iat[6] == "S"):
                temp.append(np.float32(0))
            elif (value.iat[6] == "C"):
                temp.append(np.float32(1))
            else:
                temp.append(np.float32(2))
            data.append(temp)
        self.data = np.array(data)    
        
    def __len__(self):
        return len(self.label)
    
    def __getitem__(self, idx):
        attributes = self.data[idx]
        label = self.label[idx]
        return attributes, label
    
class test_data:
    
    def __init__(self):
        data = []
        csv = pd.read_csv("data/test.csv")
        self.id = csv['PassengerId'].to_numpy()
        csv.drop(['PassengerId','Name','Ticket', 'Cabin'], axis=1, inplace=True)
        for key, value in csv.iterrows():
            temp = []
            temp.append(np.float32(value.iat[0]))
            temp.append(np.float32(0)) if (value.iat[1] == "male") else temp.append(np.float32(1))
            temp.append(np.float32(0)) if (np.isnan(value.iat[2])) else temp.append(np.float32(value.iat[2]))
            temp.append(np.float32(value.iat[3]))
            temp.append(np.float32(value.iat[4]))
            if (value.iat[6] == "S"):
                temp.append(np.float32(0))
            elif (value.iat[6] == "C"):
                temp.append(np.float32(1))
            else:
                temp.append(np.float32(2))
            data.append(temp)
        self.data = np.array(data)
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.id[idx], self.data[idx]
    
class early_stopper:
    # At each epoch, see if avg validation loss is decreasing
    # if its the 3rd epoch, return True else false
    def __init__(self, patience = 3, min_delta = 0):  
        self.counter = 0
        self.patience = 3
        self.min_delta = 0
        self.min_validation_loss = float('inf')
        
    def early_stop(self, validation_loss):
        if validation_loss < self.min_validation_loss:
            self.min_validation_loss = validation_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                return True
            
# hyperparameters to tune            
epochs = 50
batch_size = 64
validation_split = 0.2
shuffle_dataset = True      
        
class MLP(nn.Module):
    
    def __init__(self):
        # use superclass init to get .parameters()
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(6, 12),
            nn.ReLU(),
            nn.Linear(12,24),
            nn.ReLU(),
            nn.Linear(24,1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        return self.layers(x)

def train():
    model = MLP()      
    training_loss = []
    testing_loss = []
    
    # split training and validation data from dataset
    dataset = train_data()
    dataset_size = len(dataset)
    indices = list(range(dataset_size))
    split = int(np.floor(validation_split * dataset_size))
    if shuffle_dataset :
        np.random.seed(12)
        np.random.shuffle(indices)
    train_indices, val_indices = indices[split:], indices[:split]

    # Creating PT data samplers and loaders:
    train_sampler = SubsetRandomSampler(train_indices)
    valid_sampler = SubsetRandomSampler(val_indices)                
            
    train_loader = DataLoader(dataset, batch_size=batch_size, sampler=train_sampler)
    validation_loader = DataLoader(dataset, batch_size=batch_size, sampler=valid_sampler)

    # set loss as Binary Cross Entropy with SGD optimizer
    loss_func = nn.BCELoss()
    optimizer = torch.optim.SGD(model.parameters(), lr = 0.0001)
    
    # create early stopping if validation loss does not decrease
    early_stopping = early_stopper(patience=3)
    
    for epoch in range(epochs):
        print(f"--- Training Epoch {epoch+1} now ---")
        step_loss = []
        
        model.train()
        for i, data in enumerate(train_loader):
            # forward and backward pass for one mini batch
            feature, target = data
            target = torch.unsqueeze(target, 1)
            optimizer.zero_grad()
            y_pred = model.forward(feature)
            loss = loss_func(y_pred, target)
            loss.backward()
            optimizer.step()
            step_loss.append(loss.item())
        
        avg_training_loss = np.mean(np.array(step_loss))
        print(f"* Epoch: {epoch+1}, Avg training loss: {avg_training_loss:.4f} *")
        training_loss.append(avg_training_loss)
        
        # set eval mode for validation set
        model.eval()
        with torch.no_grad():
            validation_step_loss = []
            for i, data in enumerate(validation_loader):
                feature, target = data
                target = torch.unsqueeze(target, 1)
                y_pred = model.forward(feature)
                loss = loss_func(y_pred, target)
                validation_step_loss.append(loss.item())
                
            avg_validation_loss = np.mean(np.array(validation_step_loss))
            print(f"* Epoch: {epoch+1}, Avg validation loss: {avg_validation_loss:.4f} *")
            testing_loss.append(avg_validation_loss)
            
        # if avg validation loss of epoch does not decrease after 3 epoch, break
        if early_stopping.early_stop(avg_validation_loss):
            break
        
    # plot training vs validation loss graph
    plt.plot(training_loss, label='train_loss')
    plt.plot(testing_loss,label='val_loss')
    plt.legend()
    plt.savefig("model_loss.png")
    
    # save model 
    torch.save(model.state_dict(), "model/model.pt")
    
    print("--- Finished Training ---")

def test():
    
    # set model in evaluation mode
    model.eval()
    with torch.no_grad():
        dataset = test_data()
        test_loader = DataLoader(dataset)
        output = []
        for entry in test_loader:
            id, feature = entry
            # convert tensor output to numpy 2d matrix
            temp = model.forward(feature).numpy()
            pred = np.where( temp[0][0]> 0.5, 1, 0)
            output.append(pred)
    output = np.array(output)
    # create panda dataframe to output as csv
    dataset = pd.DataFrame({'PassengerId': dataset.id, 'Survived': output})
    dataset.to_csv("output.csv", index = False)
    print("Outputting predictions.")

# if training model, set training to TRUE
# elif testing, set training to False
training = False

if training:
    train()
else:
    model = MLP()
    model.load_state_dict(torch.load("model/model.pt"))
    test()