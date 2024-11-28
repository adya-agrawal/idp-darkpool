import matplotlib.pyplot as plt
import numpy as np
# Increase font size for the entire plot
plt.rcParams.update({'font.size': 20})
# Create data
# Define the range of total orders (powers of two)
x = np.array([2**i for i in range(5, 14)])  # From 32 to 8192
y1 = [0.023712, 0.046869, 0.137928, 0.187392, 0.384663, 1.002069, 2.302776, 3.929733, 7.106787]  # Plaintext total time
y2 = [0.046881, 0.140625, 0.234153, 0.452811, 0.861396, 1.735350, 3.580467, 7.440897, 15.082662]  # IDP total time
y1_executed = [32, 48, 96, 208, 368, 832, 1520, 3248, 6192]  # Mean of 3 (matching count for plaintext)
y2_executed = [28, 48, 98, 182, 376, 764, 1522, 3086, 6132]
y1_messages = [177,224,594,1142,3117, 5794, 11791, 26652, 77547]
y2_messages = [168,420,802,2134,4119, 9218,19801,42721, 77506]

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
plt.savefig('world.pdf', dpi=300)  # Save as PNG with high resolution
plt.show()