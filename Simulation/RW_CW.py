
import matplotlib.pyplot as plt
import numpy as np


def read_file(file_path):
    """Read and return the content of the given file."""
    with open(file_path, 'r') as f:
        return f.read()


def extract_durations(log_content, action, node):
    """Extract durations for the specified action and node from the log content."""
    lines = log_content.strip().split("\n")
    durations = []
    for line in lines:
        if action in line and node in line:
            try:
                duration = float(line.split("took")[1].split("seconds")[0].strip())
                durations.append(duration)
            except ValueError as e:
                print(f"Error parsing line: {line}")
    return durations

def extract_weight_durations(log_content, node):
    """Extract durations for the 'Updating Weights' action for the specified node from the log content."""
    return extract_durations(log_content, "Updating Weights", node)

def parse_file_name(file_name):
    """Parse the file name to extract N, α, and W."""
    parts = file_name.split('_')
    N = parts[0][1:]
    alpha = parts[1]

    # Extract the W value without 's' and '.txt'
    W_val = parts[2].split('s')[0].replace('.txt', '')

    # Adjust the split point based on the total length of W_val
    split_point = len(W_val) // 2
    W_start, W_end = W_val[:split_point], W_val[split_point:]

    W = f"{W_start}-{W_end}s"

    return f"N={N}, α={alpha}, W={W}"


def plot_durations(durations_list, file_names):
    """Plot durations from multiple nodes on a single graph."""

    # Colors for each line
    colors = [
        'royalblue', 'darkorange', 'forestgreen', 'firebrick', 'mediumpurple',
        'saddlebrown', 'deepskyblue', 'limegreen', 'pink', 'goldenrod',
        'midnightblue', 'aqua', 'magenta', 'yellowgreen', 'red',
        'cyan', 'lightcoral', 'darkolivegreen'
    ]
    # Get the max number of transactions across all files for x-axis
    max_transactions = max([len(durations) for durations in durations_list])

    # Create the plot
    plt.figure(figsize=(10, 6))

    for idx, durations in enumerate(durations_list):
        # Generate x-values and prepend a 0
        x = [0] + list(range(1, len(durations) + 1))
        y = [0] + durations

        # Smoothing the line to make it look like a wave (optional)
        degree = 1
        coeffs = np.polyfit(x, y, degree)
        p = np.poly1d(coeffs)
        x_smooth = list(range(max_transactions + 1))  # Extended to max transactions
        y_smooth = p(x_smooth)

        label = parse_file_name(file_names[idx])
        plt.plot(x_smooth, y_smooth, '--', color=colors[idx], markersize=2, linewidth=1, label=label)  # '--' for dashed line

    # Adding labels, title, and legend
    plt.xlabel('Transaction Count', fontsize=14, fontweight='bold')
    plt.ylabel('Duration (Seconds)', fontsize=14, fontweight='bold')
    plt.title('Duration for One Node', fontsize=16, fontweight='bold')
    legend= plt.legend(loc="upper left", fontsize=12)
    for text in legend.get_texts():
        text.set_fontweight('bold')
    plt.xlim(0, max_transactions)  # Explicitly set the x-axis limits
    # Display the plot
    plt.grid(True)
    plt.tight_layout()
    plt.show()
def plot_weight_durations_line_graph(durations_list, file_names):
    """Plot weight update durations from multiple nodes on a line graph."""
    colors = [
        'royalblue', 'darkorange', 'forestgreen', 'firebrick', 'mediumpurple',
        'saddlebrown', 'deepskyblue', 'limegreen', 'pink', 'grey',
        'goldenrod', 'midnightblue', 'aqua', 'magenta', 'yellowgreen',
        'black', 'red', 'cyan', 'lightcoral', 'darkolivegreen'
    ]
    plt.figure(figsize=(10, 6))

    for idx, durations in enumerate(durations_list):
        x = list(range(1, len(durations) + 1))
        y = np.clip(durations, None, 10)  # Clip values above 25 to 25
        label = parse_file_name(file_names[idx])
        plt.plot(x, y, '-', color=colors[idx], markersize=4, linewidth=2, label=label)  # '-' for solid line


    plt.xlabel('Transaction Count', fontsize=14, fontweight='bold')
    plt.ylabel('Weight Update Duration (Seconds)', fontsize=14, fontweight='bold')
    plt.title('Weight Update Duration for One Node', fontsize=16, fontweight='bold')
    # plt.legend(loc="upper right")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    all_file_paths = [
        [
            'timings_dir/N2_0.01_60120.txt',
            #'timings_dir/N4_0.01_60120.txt',
            'timings_dir/N6_0.01_60120.txt',
            'timings_dir/N2_0.0_60120.txt',
            'timings_dir/N4_0.0_60120.txt',
            'timings_dir/N6_0.0_60120.txt',
            'timings_dir/N2_0.001_60120.txt',
            'timings_dir/N4_0.001_60120.txt',
            'timings_dir/N6_0.001_60120.txt'
        ],
        [
            'timings_dir/N2_0.01_120240.txt',
            #'timings_dir/N4_0.01_120240.txt',
            'timings_dir/N6_0.01_120240.txt',
            'timings_dir/N2_0.0_120240.txt',
            'timings_dir/N4_0.0_120240.txt',
            'timings_dir/N6_0.0_120240.txt',
            'timings_dir/N2_0.001_120240.txt',
            'timings_dir/N4_0.001_120240.txt',
            'timings_dir/N6_0.001_120240.txt'
        ]
    ]

    all_nodes = [
        ["(Node: Node 4)"] * 8,
        ["(Node: Node 4)"] * 8
    ]

    for file_paths, nodes in zip(all_file_paths, all_nodes):
        file_names = [file_path.split('/')[-1] for file_path in file_paths]
        durations_list = []
        weights_durations_list = []  # for weights updating durations

        for i, file_path in enumerate(file_paths):
            log_content = read_file(file_path)
            node_durations = extract_durations(log_content, "Random walk tip selction", nodes[i])
            durations_list.append(node_durations)
            # For Updating Weights
            weight_durations = extract_weight_durations(log_content, nodes[i])
            weights_durations_list.append(weight_durations)

        plot_durations(durations_list, file_names)
        #Uncomment the below line if you have a function to plot the weights updating durations
        plot_weight_durations_line_graph(weights_durations_list, file_names)


if __name__ == "__main__":
    main()

