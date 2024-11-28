import matplotlib.pyplot as plt
import numpy as np
# Increase font size for the entire plot
plt.rcParams.update({'font.size': 20})
# Create data
# Define the range of total orders (powers of two)
x = np.array([2**i for i in range(5, 14)])  # From 32 to 8192
y1 = [0.021963, 0.046887, 0.093768, 0.187503, 0.314547, 0.690672, 1.188615, 2.645862, 6.717666]  # Plaintext total time
y2 = [0.046899, 0.093771, 0.221568, 0.455574, 0.864021, 1.711437, 3.336609, 6.797175, 14.694054]  # IDP total time
y1_executed = [32, 48, 96, 192, 352, 752, 1520, 3184, 6256]  # Mean of 3 (matching count for plaintext)
y2_executed = [22, 48, 96, 192, 382, 756, 1542, 3050, 6130]
y1_messages = [122,284,502,904, 2367, 5825, 7283, 20026, 49297]
y2_messages = [169,373,736,1638,3951, 6435, 15316, 27385, 63386]

plt.figure(figsize=(10, 6))

# Plot total time taken
plt.plot(x, y1, label='Non Private Auction', marker='o', color='blue')
plt.plot(x, y2, label='Indifferentially Private Auction', marker='o', color='red')
plt.title('Total Time Taken vs Total Orders')
plt.xlabel('Total Orders (Powers of Two)')
plt.ylabel('Total Time (seconds)')
plt.xscale('log', base=2)
plt.yscale('log', base=2) # Set x-axis to logarithmic scale with base 2
plt.ylim(2**-7, 2**5)
plt.xticks(x)  # Set x-ticks to the values in x
plt.xticks(rotation=45)  # Rotate x-axis labels
plt.legend()
plt.grid()

# Adjust layout to prevent overlap
plt.tight_layout()

# Save the plot as an image
plt.savefig('global.pdf', dpi=300)  # Save as PNG with high resolution
plt.show()