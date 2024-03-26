from settings import *
from utils import *
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pickle

def plot_heatmap(data, data_name, plot_n):
    global collection_name
    # Compute the probability matrix of a cell being prefilled (gray cell)
    first_layout_matrix = next(iter(data.values()))['layout']
    matrix_sum = np.zeros_like(first_layout_matrix, dtype=np.float64) 
    for entry in data.values():            
        layout_array = np.array(entry['layout'])
        matrix_sum += layout_array 
    matrix_sum = matrix_sum / len(data)

    # Plot the matrix as a heatmap
    plt.figure(plot_n)
    plt.imshow(matrix_sum, cmap='gray_r', interpolation='nearest')
    plt.colorbar()
    plt.title(f'Heatmap de celdas grises, n = {len(data)}, crucigramas tipo {data_name}')
    plt.show(block = False)

def main():
    n = len(ANALYSIS_COLLECTIONS)
    datasets = []
    for i in range(0, n):
        try:
            with open(ANALYSIS_DATA_FILES[i], 'rb') as f:
                data_dict = pickle.load(f)
                datasets.append(data_dict)
        except Exception as e:
            print("Data file not found!")
            print(e)
            return
        print(f"Found data for collection {ANALYSIS_COLLECTIONS[i]} with {len(data_dict)} entries, running analysis...")
    for i in range(0, n):
        plot_heatmap(datasets[i], ANALYSIS_COLLECTIONS[i], i+1)
    input("Press Enter to continue...")

if __name__ == "__main__":
    main()


