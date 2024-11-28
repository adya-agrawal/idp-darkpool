import matplotlib.pyplot as plt
import numpy as np

# Increase font size for the entire plot
plt.rcParams.update({'font.size': 20})

# Create data
# Define the range of total orders (powers of two)
x = np.array([2**i for i in range(5, 14)])  # From 32 to 8192
y1 = [0.014889, 0.045030, 0.046872, 0.140736, 0.279633, 0.475998, 0.953937, 1.783707, 3.887790]  # Plaintext total time
y2 = [0.046884, 0.093642, 0.234408, 0.392547, 0.768807, 1.520427, 3.101742, 6.606381, 13.328184]  # IDP total time
y1_executed = [32, 48, 96, 208, 480, 768, 1488, 2976, 6160]  # Mean of 3 (matching count for plaintext)
y2_executed = [24, 48, 96, 186, 380, 776, 1554, 3070, 6134]
y1_messages = [102,169,323,626, 1442, 2309, 4828, 8991, 19232]
y2_messages = [168,336,659,1292,2623, 5215, 10377, 21156, 42345]

plt.figure(figsize=(10, 6))

# Plot total time taken
plt.plot(x, y1, label='Non Private Auction', marker='o', color='blue')
plt.plot(x, y2, label='Indifferentially Private Auction', marker='o', color='red')
plt.title('Total Time Taken vs Total Orders')
plt.xlabel('Total Orders (Powers of Two)')
plt.ylabel('Total Time (seconds)')
plt.xscale('log', base=2) # Set x-axis to logarithmic scale with base 2
plt.yscale('log', base=2)
plt.ylim(2**-7, 2**5)
plt.xticks(x)  # Set x-ticks to the values in x
plt.xticks(rotation=45)  # Rotate x-axis labels
plt.legend()
plt.grid()

# Adjust layout to prevent overlap
plt.tight_layout()

# Save the plot as an image
plt.savefig('local.pdf', dpi=300)  # Save as PNG with high resolution
plt.show()