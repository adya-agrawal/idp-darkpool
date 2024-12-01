import matplotlib.pyplot as plt
import numpy as np
# Increase font size for the entire plot
plt.rcParams.update({'font.size': 20})
# Create data
# Define the range of total orders (powers of two)
x = np.array([2**i for i in range(3, 9)])
y1 = [4.473477, 7.685844, 15.835275, 31.789683, 66.598242, 146.548425]  # Plaintext total time
y2 = [16.219227, 30.659232, 58.022745, 115.010172, 220.162902, 478.396692]  # IDP total time


plt.figure(figsize=(10, 6))

# Plot total time taken
plt.plot(x, y1, label='Non Private Auction', marker='o', color='blue')
plt.plot(x, y2, label='Indifferentially Private Auction', marker='o', color='red')
plt.title('Total Time Taken vs Number of Orders per Client')
plt.xlabel('Total Orders per Client (Powers of Two)')
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
plt.savefig('order.pdf', dpi=300)  # Save as PNG with high resolution
plt.show()