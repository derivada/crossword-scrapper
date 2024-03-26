from settings import *
from utils import *
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pickle

def plot_heatmap():
    global data_dict
    # Compute the probability matrix of a cell being prefilled (gray cell)
    first_layout_matrix = next(iter(data_dict.values()))['layout']
    matrix_sum = np.zeros_like(first_layout_matrix, dtype=np.float64) 
    for entry in data_dict.values():            
        layout_array = np.array(entry['layout'])
        matrix_sum += layout_array 
    matrix_sum = matrix_sum / len(data_dict)

    # Plot the matrix as a heatmap
    plt.imshow(matrix_sum, cmap='gray_r', interpolation='nearest')
    plt.colorbar()
    plt.title(f'Heatmap de celdas grises')
    plt.show()

data_dict = {}

def main():
    global data_dict
    try:
        with open(DATA_FILE, 'rb') as f:
            loaded_data = pickle.load(f)
        data_dict = loaded_data
    except Exception as e:
        print("Data file not found!")
        print(e)
        return
    print(f"Found existing data with {len(data_dict)} entries")
    print(f"Approximate size of loaded data: {data_size(data_dict)}")
    plot_heatmap()

if __name__ == "__main__":
    main()


