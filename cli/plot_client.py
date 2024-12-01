import matplotlib.pyplot as plt
import numpy as np
# Increase font size for the entire plot
plt.rcParams.update({'font.size': 20})
# Create data
# Define the range of total orders (powers of two)
x = np.array([2**i for i in range(9, 14)])
y1 = [4.473477, 8.998527, 18.649776, 35.205729, 71.291664]  # Plaintext total time
y2 = [14.318967, 33.019419, 75.825309, 185.904909, 540.404421]  # IDP total time


plt.figure(figsize=(10, 6))

# Plot total time taken
plt.plot(x, y1, label='Non Private Auction', marker='o', color='blue')
plt.plot(x, y2, label='Indifferentially Private Auction', marker='o', color='red')
plt.title('Total Time Taken vs Number of Clients')
plt.xlabel('Total Clients (Powers of Two)')
plt.ylabel('Total Time (seconds)')
plt.xscale('log', base=2)
plt.yscale('log', base=2) # Set x-axis to logarithmic scale with base 2
plt.ylim(2**2, 2**10)
plt.xticks(x)  # Set x-ticks to the values in x
plt.xticks(rotation=45)  # Rotate x-axis labels
plt.legend()
plt.grid()

# Adjust layout to prevent overlap
plt.tight_layout()

# Save the plot as an image
plt.savefig('client.pdf', dpi=300)  # Save as PNG with high resolution
plt.show()