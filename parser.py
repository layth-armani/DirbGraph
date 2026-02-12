import matplotlib.pyplot as plt
import igraph as ig
import sys

# Init graph
graph = ig.Graph(directed = True)
base_domain_name = ""


############ UTILS #############

# Extracts object name and info
def parseObjectLine(file_line):
    cleaned_string = file_line.lstrip("+ ") # Clean '+' char
    split_line = cleaned_string.rsplit("/", 1) # Splits into [base_url , object name and info]
    return split_line[1].strip()

# Extracts full directory name 
def parseDirectoryLine(dir_line):
    split_string = dir_line.split()
    return split_string[2]

# Check if current line is a sub-directory 
def detectDir(string):
    if "==> DIRECTORY:" in string:
        return True
    return False

# Check if current line is base URL section
def isBaseUrl(string):
    if "URL_BASE:" in string:
        return True
    return False 

# Check if current line is pre-scan section
def isAtFirstScan(string):
    if "GENERATED WORDS:" in string:
        return True
    return False 

# Return the list of objects tied to a domain
def collectDirObjects(file):
    object_list = []
    line = file.readline()

    while line != "\n":
        if detectDir(line):
            object_list.append(parseDirectoryLine(line))
        else:
            object_list.append(parseObjectLine(line))
        line = file.readline()
    
    return object_list
        

def parseDirbFile(filename):
    global base_domain_name

    # Add all lines of text file to a list
    with  open(filename, "rt") as f:
        line = f.readline()
        while isBaseUrl(line) == False:
            line = f.readline()

        # base URL is detected 
        base_domain_name = line.strip()

        # Iterate till the scan of base URL
        while isAtFirstScan(line) == False:
            line = f.readline()

        # Skip two lines after "GENERATED WORDS" section
        next(f)
        next(f)

        first_list = collectDirObjects(f)

        graph.add_vertices([base_domain_name] + first_list)
        graph.add_edges([(base_domain_name, obj) for obj in first_list])

        layout = graph.layout("tree")

        # Scale figure width based on number of nodes for spacing
        node_count = graph.vcount()
        fig_width = max(14, node_count * 0.6)
        fig_height = max(6, fig_width * 0.2)

        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ig.plot(graph, layout=layout, target=ax, margin=40,
                vertex_size=20, vertex_label_size=7,
                edge_width=0.5, edge_arrow_size=0.5, edge_arrow_width=0.5)
        plt.title("DIRB Scan Graph")
        plt.tight_layout()
        plt.show()

    
parseDirbFile(sys.argv[1])





#print(parseFileLine("+ https://www.epfl.ch/en/.bash_history (CODE:403|SIZE:813675)"))
#print(parseDirectoryLine("==> DIRECTORY: https://www.epfl.ch/en/feed/"))
